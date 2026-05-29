"""Check that automation opens the expected Gemini Gem (e.g. 스크립트 정리 도우미)."""

import asyncio
import os
import re

from dotenv import load_dotenv
from playwright.async_api import async_playwright

from gemini_session import (
    extract_gem_id,
    launch_gemini_context,
    open_gem_conversation,
    resolve_data_path,
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


async def read_visible_gem_title(page) -> str:
    selectors = [
        "h1",
        "h2",
        '[class*="gem"] h1',
        '[class*="gem"] h2',
        "header h1",
        "header h2",
        '[data-test-id*="gem"]',
    ]
    for sel in selectors:
        loc = page.locator(sel)
        count = min(await loc.count(), 5)
        for i in range(count):
            try:
                text = (await loc.nth(i).inner_text(timeout=2000)).strip()
                if text and len(text) < 120:
                    return text
            except Exception:
                continue
    return ""


async def page_contains(page, needle: str) -> bool:
    try:
        body = await page.locator("body").inner_text(timeout=5000)
        return needle in body
    except Exception:
        return False


async def main() -> None:
    load_dotenv()
    gem_url = os.getenv("GEMINI_GEM_URL", "").strip().split("?")[0]
    expected_name = os.getenv("GEMINI_GEM_EXPECTED_NAME", "스크립트 정리 도우미").strip()
    configured_id = extract_gem_id(gem_url)
    profile = resolve_data_path(os.getenv("PLAYWRIGHT_PROFILE_DIR", "./chrome_profile"), SCRIPT_DIR)

    print("=== Gem verification ===")
    print(f"Configured URL : {gem_url}")
    print(f"Configured ID  : {configured_id}")
    print(f"Expected name  : {expected_name}")
    print(f"Profile        : {profile}")
    print()

    class _Settings:
        profile_dir = profile
        gemini_storage_state_file = resolve_data_path(
            os.getenv("GEMINI_STORAGE_STATE_FILE", "./gemini_storage_state.json"),
            SCRIPT_DIR,
        )
        auto_login_wait_sec = int(os.getenv("AUTO_LOGIN_WAIT_SEC", "300"))
        headless = os.getenv("HEADLESS", "false").strip().lower() in {"1", "true", "yes"}

    settings = _Settings()

    async with async_playwright() as p:
        context, page = await launch_gemini_context(p, settings)
        try:
            await open_gem_conversation(page, gem_url)
            await page.wait_for_timeout(2000)

            final_url = page.url
            url_slug = ""
            m = re.search(r"/gem/([^/?#]+)", final_url)
            if m:
                url_slug = m.group(1)

            title = await read_visible_gem_title(page)
            name_in_page = await page_contains(page, expected_name)
            id_in_url = configured_id in final_url
            id_in_href = await page.locator(f'a[href*="{configured_id}"]').count() > 0

            screenshot = os.path.join(SCRIPT_DIR, "verify_gem_screenshot.png")
            await page.screenshot(path=screenshot, full_page=False)

            print(f"Final URL      : {final_url}")
            print(f"URL slug       : {url_slug}")
            print(f"Visible title  : {title!r}")
            print(f"Name on page   : {name_in_page} (search: {expected_name!r})")
            print(f"Config ID in URL: {id_in_url}")
            print(f"Screenshot     : {screenshot}")
            print()

            ok = name_in_page or (expected_name and expected_name in title)
            if url_slug and url_slug != configured_id:
                print(
                    "NOTE: Google often redirects /gem/<share-id> to a shorter session slug. "
                    "That alone does not mean the wrong Gem."
                )

            if ok:
                print("RESULT: OK — expected Gem name found on page.")
            else:
                print(
                    "RESULT: UNCERTAIN — Gem name not found in UI. "
                    "Open screenshot and confirm the Gem header manually."
                )
        finally:
            await context.close()


if __name__ == "__main__":
    asyncio.run(main())
