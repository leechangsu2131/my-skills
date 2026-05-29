"""Gemini browser session: persistent profile, backup storage state, interactive login recovery."""

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING, Any, Callable, Optional

from playwright.async_api import BrowserContext, Page

if TYPE_CHECKING:
    from main import Settings

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def resolve_data_path(path: str, base_dir: Optional[str] = None) -> str:
    base = base_dir or SCRIPT_DIR
    if os.path.isabs(path):
        return os.path.normpath(path)
    return os.path.normpath(os.path.join(base, path))


def extract_gem_id(gem_url: str) -> str:
    return gem_url.rstrip("/").split("/")[-1]


def is_google_login_url(url: str) -> bool:
    lower = url.lower()
    return (
        "accounts.google.com" in lower
        or "signin" in lower
        or "servicelogin" in lower
        or "oauth" in lower and "google" in lower
    )


async def has_gemini_chat_input(page: Page, timeout_ms: int = 8000) -> bool:
    selectors = [
        "rich-textarea[aria-label*='메시지']",
        "rich-textarea[aria-label*='message']",
        "rich-textarea",
        "div[contenteditable='true']:visible:not(.ql-clipboard)",
        "textarea:visible",
    ]
    for sel in selectors:
        locator = page.locator(sel).first
        if await locator.count() == 0:
            continue
        try:
            await locator.wait_for(state="visible", timeout=timeout_ms)
            return True
        except Exception:
            continue
    return False


async def is_gemini_session_valid(page: Page) -> bool:
    try:
        await page.goto("https://gemini.google.com/app", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(2500)
    except Exception:
        return False

    if is_google_login_url(page.url):
        return False
    if "gemini.google.com" not in page.url:
        return False
    return await has_gemini_chat_input(page, timeout_ms=10000)


async def save_storage_state(context: BrowserContext, path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    await context.storage_state(path=path)
    print(f"Saved Gemini session backup: {path}")


async def wait_for_interactive_login(page: Page, timeout_sec: int) -> bool:
    print(
        f"브라우저에서 Google/Gemini 로그인을 완료해 주세요. "
        f"최대 {timeout_sec}초 대기하며, 완료되면 자동으로 진행합니다."
    )
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        await page.wait_for_timeout(2000)
        url = page.url
        if is_google_login_url(url):
            continue
        if "gemini.google.com" in url:
            await page.wait_for_timeout(2500)
            if not is_google_login_url(page.url):
                if await has_gemini_chat_input(page, timeout_ms=12000):
                    print("로그인 완료 및 Gemini 채팅 UI 확인.")
                    return True
                if "gemini.google.com" in page.url and not is_google_login_url(page.url):
                    print("로그인 완료 (Gemini 페이지 진입).")
                    return True
    print("로그인 대기 시간 초과.")
    return False


async def try_context_with_storage_backup(
    playwright: Any,
    settings: Settings,
    headless: bool,
) -> Optional[tuple[BrowserContext, Page]]:
    backup = settings.gemini_storage_state_file
    if not os.path.exists(backup):
        return None

    print(f"프로필 세션 무효 — 백업 세션 복원 시도: {backup}")
    browser = await playwright.chromium.launch(
        headless=headless,
        channel="chrome",
        args=["--disable-blink-features=AutomationControlled"],
    )
    context = await browser.new_context(storage_state=backup)
    page = await context.new_page()
    if await is_gemini_session_valid(page):
        print("백업 storage state로 세션 복원 성공.")
        return context, page

    await context.close()
    await browser.close()
    return None


async def launch_gemini_context(
    playwright: Any,
    settings: Settings,
    on_login_required: Optional[Callable[[], None]] = None,
) -> tuple[BrowserContext, Page]:
    """Launch browser with durable profile; recover login via backup or headed auto-wait."""
    profile = settings.profile_dir
    os.makedirs(profile, exist_ok=True)
    launch_args = ["--disable-blink-features=AutomationControlled"]

    async def open_persistent(headless: bool) -> tuple[BrowserContext, Page]:
        context = await playwright.chromium.launch_persistent_context(
            user_data_dir=profile,
            headless=headless,
            channel="chrome",
            args=launch_args,
        )
        page = await context.new_page()
        return context, page

    context, page = await open_persistent(settings.headless)
    if await is_gemini_session_valid(page):
        return context, page

    await context.close()

    restored = await try_context_with_storage_backup(playwright, settings, settings.headless)
    if restored:
        context, page = restored
        await save_storage_state(context, settings.gemini_storage_state_file)
        return context, page

    if on_login_required:
        try:
            on_login_required()
        except Exception as exc:
            print(f"Login notification failed: {exc}")

    print("로그인 필요 — 브라우저를 표시하고 로그인 완료를 기다립니다.")
    context, page = await open_persistent(headless=False)
    await page.goto("https://gemini.google.com/app", wait_until="domcontentloaded", timeout=60000)

    if not await wait_for_interactive_login(page, settings.auto_login_wait_sec):
        await context.close()
        raise RuntimeError(
            "Gemini 로그인 실패. 브라우저에서 Google 계정 로그인(2단계 인증 포함)을 완료한 뒤 "
            "SETUP_LOGIN_ONLY=1 로 다시 시도하세요."
        )

    await save_storage_state(context, settings.gemini_storage_state_file)
    return context, page


async def verify_gem_identity(page: Page, gem_url: str, expected_name: str = "") -> None:
    """Warn or fail if the opened page does not show the expected Gem name."""
    if not expected_name:
        return
    try:
        body = await page.locator("body").inner_text(timeout=8000)
    except Exception:
        print(f"Gem name check skipped (could not read page): expected {expected_name!r}")
        return
    if expected_name in body:
        print(f"Gem verified on page: {expected_name!r}")
        return
    configured_id = extract_gem_id(gem_url)
    if configured_id in page.url:
        print(f"Gem URL contains configured id: {configured_id}")
        return
    raise RuntimeError(
        f"Expected Gem {expected_name!r} not found on page. "
        f"URL={page.url}. Check GEMINI_GEM_URL in .env."
    )


async def open_gem_conversation(
    page: Page,
    gem_url: str,
    expected_gem_name: str = "",
) -> None:
    """Open the configured Gem. Accepts /app redirect when chat input is available."""
    if "/gem/" not in gem_url:
        raise ValueError(f"GEMINI_GEM_URL must be a Gem link (/gem/...): {gem_url}")

    gem_id = extract_gem_id(gem_url)
    print(f"Opening Gem: {gem_url}")

    targets = [
        gem_url,
        f"https://gemini.google.com/app/{gem_id}",
    ]

    for target in targets:
        await page.goto(target, wait_until="load", timeout=60000)
        await page.wait_for_timeout(3000)
        if is_google_login_url(page.url):
            raise RuntimeError("Gemini login required during Gem open.")
        if await has_gemini_chat_input(page, timeout_ms=15000):
            print(f"Gem UI ready at {page.url}")
            await verify_gem_identity(page, gem_url, expected_gem_name)
            return

    await _open_gem_via_gems_library(page, gem_id)
    if await has_gemini_chat_input(page, timeout_ms=15000):
        print(f"Gem UI ready (via Gems library) at {page.url}")
        await verify_gem_identity(page, gem_url, expected_gem_name)
        return

    raise RuntimeError(
        f"Could not open Gem chat UI. Current URL: {page.url}. "
        "로그인 상태와 GEMINI_GEM_URL을 확인하세요."
    )


async def _open_gem_via_gems_library(page: Page, gem_id: str) -> None:
    await page.goto("https://gemini.google.com/gems", wait_until="load", timeout=60000)
    await page.wait_for_timeout(3000)

    link = page.locator(f'a[href*="{gem_id}"]').first
    if await link.count() > 0:
        await link.click(timeout=10000)
        await page.wait_for_timeout(4000)
        return

    card = page.locator("mat-card, [data-test-id*='gem']").filter(has_text=gem_id[:8])
    if await card.count() > 0:
        await card.first.click(timeout=10000)
        await page.wait_for_timeout(4000)
