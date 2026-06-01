import asyncio
import datetime
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Optional

import requests
import schedule
import urllib3
from dotenv import load_dotenv
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright
from youtube_transcript_api import YouTubeTranscriptApi

from gemini_session import (
    GeminiLoginRequired,
    launch_gemini_context,
    looks_like_login_wall_text,
    open_gem_conversation,
    resolve_data_path,
    save_storage_state,
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


@dataclass
class Settings:
    channel_url: str
    title_prefix: str
    gemini_gem_url: str
    send_target: str
    discord_webhook: str
    discord_bot_token: str
    discord_channel_id: str
    kakao_token: str
    kakao_rest_api_key: str
    kakao_redirect_uri: str
    kakao_token_file: str
    processed_file: str
    run_time: str
    profile_dir: str
    gemini_storage_state_file: str
    auto_login_wait_sec: int
    headless: bool
    language_priority: list[str]
    response_timeout_ms: int
    max_message_length: int
    transcript_retry_interval_sec: int
    transcript_max_tries: int
    gemini_input_max_chars: int
    only_weekdays: bool
    yt_no_check_certificates: bool
    disable_ssl_verify: bool
    gemini_debug_hold_ms: int
    gemini_force_pro: bool
    gemini_use_gem_prompt: bool
    gemini_gem_expected_name: str
    gemini_min_response_chars: int
    discord_max_message_length: int


def bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def load_settings() -> Settings:
    load_dotenv()

    channel_url = os.getenv("CHANNEL_URL", "").strip()
    title_prefix = os.getenv("TITLE_PREFIX", "[체슬리모닝브리프]").strip()
    gemini_gem_url = os.getenv("GEMINI_GEM_URL", "").strip().split("?")[0]
    send_target = os.getenv("SEND_TARGET", "discord").strip().lower()
    discord_webhook = os.getenv("DISCORD_WEBHOOK", "").strip()
    discord_bot_token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
    discord_channel_id = os.getenv("DISCORD_CHANNEL_ID", "").strip()
    kakao_token = os.getenv("KAKAO_TOKEN", "").strip()
    kakao_rest_api_key = os.getenv("KAKAO_REST_API_KEY", "").strip()
    kakao_redirect_uri = os.getenv("KAKAO_REDIRECT_URI", "https://example.com").strip()
    kakao_token_file = os.getenv("KAKAO_TOKEN_FILE", "./kakao_token.json").strip()
    processed_file = resolve_data_path(os.getenv("PROCESSED_FILE", "./processed.json").strip(), SCRIPT_DIR)
    run_time = os.getenv("RUN_TIME", "16:00").strip()
    profile_dir = resolve_data_path(
        os.getenv("PLAYWRIGHT_PROFILE_DIR", "./chrome_profile").strip(),
        SCRIPT_DIR,
    )
    gemini_storage_state_file = resolve_data_path(
        os.getenv("GEMINI_STORAGE_STATE_FILE", "./gemini_storage_state.json").strip(),
        SCRIPT_DIR,
    )

    if not channel_url:
        raise ValueError("CHANNEL_URL is required")
    if not gemini_gem_url:
        raise ValueError("GEMINI_GEM_URL is required")
    if send_target == "discord" and not discord_webhook:
        raise ValueError("DISCORD_WEBHOOK is required when SEND_TARGET=discord")
    if send_target == "discord_bot" and (not discord_bot_token or not discord_channel_id):
        raise ValueError("DISCORD_BOT_TOKEN and DISCORD_CHANNEL_ID are required when SEND_TARGET=discord_bot")
    if send_target == "kakao" and not kakao_token and not kakao_rest_api_key:
        raise ValueError("Set KAKAO_TOKEN or KAKAO_REST_API_KEY + token file.")

    return Settings(
        channel_url=channel_url,
        title_prefix=title_prefix,
        gemini_gem_url=gemini_gem_url,
        send_target=send_target,
        discord_webhook=discord_webhook,
        discord_bot_token=discord_bot_token,
        discord_channel_id=discord_channel_id,
        kakao_token=kakao_token,
        kakao_rest_api_key=kakao_rest_api_key,
        kakao_redirect_uri=kakao_redirect_uri,
        kakao_token_file=kakao_token_file,
        processed_file=processed_file,
        run_time=run_time,
        profile_dir=profile_dir,
        gemini_storage_state_file=gemini_storage_state_file,
        auto_login_wait_sec=int(os.getenv("AUTO_LOGIN_WAIT_SEC", "300")),
        headless=bool_env("HEADLESS", False),
        language_priority=[s.strip() for s in os.getenv("TRANSCRIPT_LANGS", "ko,en").split(",") if s.strip()],
        response_timeout_ms=int(os.getenv("RESPONSE_TIMEOUT_MS", "120000")),
        max_message_length=int(os.getenv("KAKAO_MAX_MESSAGE_LENGTH", "1000")),
        transcript_retry_interval_sec=int(os.getenv("TRANSCRIPT_RETRY_INTERVAL_SEC", "180")),
        transcript_max_tries=int(os.getenv("TRANSCRIPT_MAX_TRIES", "10")),
        gemini_input_max_chars=int(os.getenv("GEMINI_INPUT_MAX_CHARS", "8000")),
        only_weekdays=bool_env("ONLY_WEEKDAYS", True),
        yt_no_check_certificates=bool_env("YT_NO_CHECK_CERTIFICATES", True),
        disable_ssl_verify=bool_env("DISABLE_SSL_VERIFY", True),
        gemini_debug_hold_ms=int(os.getenv("GEMINI_DEBUG_HOLD_MS", "0")),
        gemini_force_pro=bool_env("GEMINI_FORCE_PRO", True),
        gemini_use_gem_prompt=bool_env("GEMINI_USE_GEM_PROMPT", True),
        gemini_gem_expected_name=os.getenv("GEMINI_GEM_EXPECTED_NAME", "스크립트 정리 도우미").strip(),
        gemini_min_response_chars=int(os.getenv("GEMINI_MIN_RESPONSE_CHARS", "400")),
        discord_max_message_length=int(os.getenv("DISCORD_MAX_MESSAGE_LENGTH", "1900")),
    )


def split_message_chunks(message: str, max_len: int) -> list[str]:
    """Split long text for Discord (2000 char limit per message)."""
    text = message.strip()
    if not text:
        return [""]
    if len(text) <= max_len:
        return [text]

    chunks: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= max_len:
            chunks.append(remaining)
            break
        window = remaining[:max_len]
        split_at = window.rfind("\n\n")
        if split_at < max_len // 3:
            split_at = window.rfind("\n")
        if split_at < max_len // 3:
            split_at = window.rfind(" ")
        if split_at < max_len // 3:
            split_at = max_len
        chunk = remaining[:split_at].rstrip()
        if not chunk:
            chunk = remaining[:max_len]
            split_at = max_len
        chunks.append(chunk)
        remaining = remaining[split_at:].lstrip()
    return chunks


def is_weekday() -> bool:
    return datetime.datetime.now().weekday() < 5


def load_processed_ids(path: str) -> set[str]:
    if not os.path.exists(path):
        return set()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return {str(item) for item in data if item}
        return set()
    except Exception:
        return set()


def save_processed_ids(path: str, ids: set[str]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sorted(ids), f, ensure_ascii=False, indent=2)


def find_todays_live_video(settings: Settings) -> Optional[tuple[str, str]]:
    today = datetime.date.today()
    today_yy_mm_dd = today.strftime("%y/%m/%d")
    today_yyyy_mm_dd = today.strftime("%Y/%m/%d")
    command = [
        sys.executable,
        "-m",
        "yt_dlp",
        "--flat-playlist",
        "--dump-json",
        "--playlist-end",
        "20",
        settings.channel_url.rstrip("/") + "/streams",
    ]
    if settings.yt_no_check_certificates:
        command.insert(3, "--no-check-certificates")
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="ignore")

    if result.returncode != 0:
        print(f"yt-dlp failed: {result.stderr.strip()}")
        return None

    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        try:
            video = json.loads(line)
        except json.JSONDecodeError:
            continue

        title = str(video.get("title", ""))
        has_prefix = title.startswith(settings.title_prefix) if settings.title_prefix else True
        has_today_token = (today_yy_mm_dd in title) or (today_yyyy_mm_dd in title)
        if has_prefix and has_today_token:
            video_id = video.get("id")
            print(f"Found today's live VOD: {title} / {video_id}")
            return video_id, title

    return None


def find_todays_live_video_id(settings: Settings) -> Optional[str]:
    found = find_todays_live_video(settings)
    return found[0] if found else None


async def get_youtube_transcript(video_id: str, languages: list[str]) -> str:
    api = YouTubeTranscriptApi()
    fetched = api.fetch(video_id, languages=languages)
    return " ".join(snippet.text.strip() for snippet in fetched if snippet.text)


def get_transcript_with_retry(settings: Settings, video_id: str) -> Optional[str]:
    for attempt in range(settings.transcript_max_tries):
        try:
            session = requests.Session()
            if settings.disable_ssl_verify:
                session.verify = False
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            api = YouTubeTranscriptApi(http_client=session)
            fetched = api.fetch(video_id, languages=settings.language_priority)
            joined = " ".join(snippet.text.strip() for snippet in fetched if snippet.text)
            if joined:
                print(f"Transcript collected: {len(joined)} chars")
                return joined
        except Exception as exc:
            remaining = settings.transcript_max_tries - attempt - 1
            print(
                f"Transcript not ready ({attempt + 1}/{settings.transcript_max_tries}): {exc}. "
                f"Remaining retries: {remaining}"
            )
        if attempt < settings.transcript_max_tries - 1:
            time.sleep(settings.transcript_retry_interval_sec)
    return None


async def wait_for_gemini_response(page, previous_count: int, timeout_ms: int) -> str:
    selector = "message-content, model-response"
    start = time.time()
    responses = page.locator(selector)
    latest_count = previous_count

    while (time.time() - start) * 1000 < timeout_ms:
        latest_count = await responses.count()
        if latest_count > previous_count:
            break
        await page.wait_for_timeout(800)

    if latest_count <= previous_count:
        raise RuntimeError("No new Gemini response detected after sending prompt.")

    last = responses.nth(latest_count - 1)
    await last.wait_for(state="visible", timeout=timeout_ms)

    # Wait until streaming finishes and text length stabilizes.
    settle_deadline = time.time() + min(180, timeout_ms / 1000)
    prev_len = 0
    stable_rounds = 0
    text = ""
    while time.time() < settle_deadline:
        stop_button = page.locator(
            "button[aria-label*='중지'], button[aria-label*='Stop'], "
            "[data-is-loading='true'], .loading"
        )
        still_generating = await stop_button.count() > 0
        text = (await last.inner_text()).strip()
        if not still_generating and len(text) == prev_len and len(text) > 0:
            stable_rounds += 1
            if stable_rounds >= 3:
                break
        else:
            stable_rounds = 0
            prev_len = len(text)
        await page.wait_for_timeout(1500)

    if not text:
        raise RuntimeError("Gemini response was empty.")
    print(f"Gemini response length: {len(text)} chars")
    return text


def validate_gemini_response(text: str, min_chars: int) -> None:
    if looks_like_login_wall_text(text):
        raise GeminiLoginRequired(
            f"Gemini response looks like a login/consent wall ({len(text)} chars)."
        )
    if len(text) < min_chars:
        raise RuntimeError(
            f"Gemini response too short ({len(text)} chars, minimum {min_chars}). "
            "로그인·모델 선택·전송 실패 여부를 확인하세요."
        )


def build_gem_prompt(transcript: str, video_title: str, use_gem_prompt: bool) -> str:
    body = transcript
    if not use_gem_prompt:
        return body
    return (
        "[긴급 지시사항: 절대 짧게 요약하지 마세요. Gem에 설정된 '스크립트 정리 도우미' 지침을 "
        "100% 우선하여 적용하세요.]\n\n"
        f'다음은 유튜브 영상 "{video_title}"의 전체 스크립트입니다:\n\n'
        f"{body}"
    )


async def _select_gemini_pro(page) -> None:
    model_btn_selectors = [
        'button:has-text("빠른")',
        'button:has-text("Flash")',
        'button:has-text("Pro")',
        ".model-selector button",
        '[data-test-id="model-selector"]',
    ]
    opened = False
    for sel in model_btn_selectors:
        btn = page.locator(sel).first
        if await btn.count() == 0:
            continue
        try:
            if await btn.is_visible():
                await btn.click(timeout=3000)
                await page.wait_for_timeout(1000)
                opened = True
                break
        except Exception:
            continue

    if not opened:
        print("Model selector not found; continuing with current model.")
        return

    pro_selectors = [
        'li:has-text("Pro")',
        '[role="menuitem"]:has-text("Pro")',
        'button:has-text("3.1 Pro")',
        'div:has-text("3.1 Pro")',
        '[role="option"]:has-text("Pro")',
    ]
    for sel in pro_selectors:
        opt = page.locator(sel).first
        if await opt.count() == 0:
            continue
        try:
            if await opt.is_visible():
                await opt.click(timeout=3000)
                await page.wait_for_timeout(800)
                print("Gemini Pro model selected.")
                return
        except Exception:
            continue
    print("Pro option not found in model menu.")


async def _find_input_box(page):
    selectors = [
        "rich-textarea[aria-label*='메시지']",
        "rich-textarea[aria-label*='message']",
        "div[contenteditable='true']:visible:not(.ql-clipboard)",
        "textarea:visible",
    ]
    for sel in selectors:
        locator = page.locator(sel).first
        if await locator.count() > 0:
            return locator
    raise RuntimeError("Gemini input box not found.")


async def _run_gemini_prompt(page, settings: Settings, text: str, video_title: str) -> str:
    if settings.gemini_force_pro:
        await _select_gemini_pro(page)

    await page.wait_for_selector(
        "rich-textarea, div[contenteditable='true'], textarea",
        timeout=30000,
    )
    response_nodes = page.locator("message-content, model-response")
    previous_count = await response_nodes.count()

    input_box = await _find_input_box(page)
    await input_box.click()
    prompt_text = build_gem_prompt(
        text[: settings.gemini_input_max_chars],
        video_title or "체슬리모닝브리프",
        settings.gemini_use_gem_prompt,
    )

    # Clipboard paste is more reliable for long Korean transcripts.
    await page.evaluate(
        "(value) => navigator.clipboard.writeText(value)",
        prompt_text,
    )
    await page.keyboard.press("Control+a")
    await page.keyboard.press("Delete")
    await page.wait_for_timeout(200)
    await page.keyboard.press("Control+v")
    await page.wait_for_timeout(800)

    await page.keyboard.press("Enter")
    await page.wait_for_timeout(700)
    # Fallback send button click when Enter does not submit.
    send_btn = page.locator(
        "button[aria-label*='전송'], button[aria-label*='Send'], "
        "[data-test-id='send-button']"
    ).first
    if await send_btn.count() > 0:
        try:
            await send_btn.click(timeout=1200)
        except Exception:
            pass

    result = await wait_for_gemini_response(
        page,
        previous_count=previous_count,
        timeout_ms=settings.response_timeout_ms,
    )
    validate_gemini_response(result, settings.gemini_min_response_chars)
    return result


async def ask_gemini_gem(settings: Settings, text: str, video_title: str = "") -> str:
    async with async_playwright() as p:

        def notify_login_required() -> None:
            send_notification(
                settings,
                "⚠️ Gemini 세션이 만료되었습니다. 브라우저 창에서 Google 로그인을 완료해 주세요. "
                "완료되면 자동으로 요약을 계속합니다.",
            )

        context = None
        page = None
        try:
            for attempt in range(2):
                force_login = attempt > 0
                if force_login:
                    print("Gemini 재로그인 시도 중...")
                context, page = await launch_gemini_context(
                    p,
                    settings,
                    on_login_required=notify_login_required,
                    gem_url=settings.gemini_gem_url,
                    force_interactive_login=force_login,
                )
                try:
                    await open_gem_conversation(
                        page,
                        settings.gemini_gem_url,
                        expected_gem_name=settings.gemini_gem_expected_name,
                    )
                    result = await _run_gemini_prompt(page, settings, text, video_title)
                    await save_storage_state(context, settings.gemini_storage_state_file)
                    return result
                except GeminiLoginRequired as exc:
                    print(f"Gemini login recovery needed: {exc}")
                    await context.close()
                    context = None
                    page = None
                    if attempt == 0:
                        continue
                    raise RuntimeError(
                        "Gemini 로그인 복구 실패. SETUP_LOGIN_ONLY=1 로 세션을 다시 저장하세요."
                    ) from exc
            raise RuntimeError("Gemini session could not be established.")
        except PlaywrightTimeoutError as exc:
            raise RuntimeError("Timed out while waiting for Gemini UI or response.") from exc
        finally:
            if page and settings.gemini_debug_hold_ms > 0:
                print(f"Holding browser for debug: {settings.gemini_debug_hold_ms}ms")
                await page.wait_for_timeout(settings.gemini_debug_hold_ms)
            if context:
                await context.close()


def _request_verify_ssl(settings: Settings) -> bool:
    verify_ssl = not settings.disable_ssl_verify
    if not verify_ssl:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    return verify_ssl


def _read_kakao_token_file(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_kakao_token_file(path: str, tokens: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tokens, f, ensure_ascii=False, indent=2)


def refresh_kakao_access_token(settings: Settings) -> str:
    if not os.path.exists(settings.kakao_token_file):
        raise FileNotFoundError(
            f"{settings.kakao_token_file} not found. Create it with initial auth code exchange first."
        )

    tokens = _read_kakao_token_file(settings.kakao_token_file)
    refresh_token = tokens.get("refresh_token", "").strip()
    if not refresh_token:
        raise ValueError("refresh_token missing in kakao token file.")

    client_id = settings.kakao_rest_api_key or tokens.get("app_key", "")
    if not client_id:
        raise ValueError("KAKAO_REST_API_KEY is required for token refresh.")

    response = requests.post(
        "https://kauth.kakao.com/oauth/token",
        data={
            "grant_type": "refresh_token",
            "client_id": client_id,
            "refresh_token": refresh_token,
        },
        timeout=20,
        verify=_request_verify_ssl(settings),
    )
    response.raise_for_status()
    payload = response.json()

    new_access = payload.get("access_token", "").strip()
    if not new_access:
        raise RuntimeError(f"Failed to refresh access token: {payload}")

    tokens["access_token"] = new_access
    if payload.get("refresh_token"):
        tokens["refresh_token"] = payload["refresh_token"]
    if "app_key" not in tokens and settings.kakao_rest_api_key:
        tokens["app_key"] = settings.kakao_rest_api_key
    _write_kakao_token_file(settings.kakao_token_file, tokens)
    return new_access


def get_kakao_access_token(settings: Settings) -> str:
    if settings.kakao_token:
        return settings.kakao_token
    return refresh_kakao_access_token(settings)


def send_kakao_message(settings: Settings, token: str, message: str, max_length: int) -> requests.Response:
    endpoint = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {"Authorization": f"Bearer {token}"}

    template_object = {
        "object_type": "text",
        "text": message[:max_length],
        "link": {
            "web_url": "https://gemini.google.com",
            "mobile_web_url": "https://gemini.google.com",
        },
    }
    payload = {"template_object": json.dumps(template_object, ensure_ascii=False)}
    response = requests.post(
        endpoint,
        headers=headers,
        data=payload,
        timeout=20,
        verify=_request_verify_ssl(settings),
    )
    return response


def send_kakao_message_with_refresh(settings: Settings, message: str) -> requests.Response:
    token = get_kakao_access_token(settings)
    response = send_kakao_message(settings, token, message, settings.max_message_length)
    if response.status_code == 401 and settings.kakao_rest_api_key:
        token = refresh_kakao_access_token(settings)
        response = send_kakao_message(settings, token, message, settings.max_message_length)
    return response


def _discord_post_content(settings: Settings, content: str) -> requests.Response:
    body = json.dumps({"content": content}, ensure_ascii=False).encode("utf-8")
    return requests.post(
        settings.discord_webhook,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        timeout=20,
        verify=_request_verify_ssl(settings),
    )


def send_discord_message(settings: Settings, message: str) -> requests.Response:
    chunks = split_message_chunks(message, settings.discord_max_message_length)
    total = len(chunks)
    last_response: Optional[requests.Response] = None
    for index, chunk in enumerate(chunks, start=1):
        prefix = f"**[{index}/{total}]**\n" if total > 1 else ""
        # Reserve space for part header (Discord hard limit: 2000).
        content = prefix + chunk
        if len(content) > 2000:
            content = chunk[:2000]
        last_response = _discord_post_content(settings, content)
        if last_response.status_code not in (200, 204):
            return last_response
        if index < total:
            time.sleep(0.6)
    return last_response  # type: ignore[return-value]


def send_discord_bot_message(settings: Settings, message: str) -> requests.Response:
    endpoint = f"https://discord.com/api/v10/channels/{settings.discord_channel_id}/messages"
    headers = {
        "Authorization": f"Bot {settings.discord_bot_token}",
        "Content-Type": "application/json",
    }
    chunks = split_message_chunks(message, settings.discord_max_message_length)
    total = len(chunks)
    last_response: Optional[requests.Response] = None
    for index, chunk in enumerate(chunks, start=1):
        prefix = f"**[{index}/{total}]**\n" if total > 1 else ""
        content = prefix + chunk
        if len(content) > 2000:
            content = chunk[:2000]
        last_response = requests.post(
            endpoint,
            headers=headers,
            json={"content": content},
            timeout=20,
            verify=_request_verify_ssl(settings),
        )
        if last_response.status_code not in (200, 201, 204):
            return last_response
        if index < total:
            time.sleep(0.6)
    return last_response  # type: ignore[return-value]


def send_notification(settings: Settings, message: str) -> requests.Response:
    if settings.send_target == "discord":
        chunks = split_message_chunks(message, settings.discord_max_message_length)
        if len(chunks) > 1:
            print(f"Discord: sending {len(chunks)} messages ({len(message)} chars total)")
        return send_discord_message(settings, message)
    if settings.send_target == "discord_bot":
        chunks = split_message_chunks(message, settings.discord_max_message_length)
        if len(chunks) > 1:
            print(f"Discord bot: sending {len(chunks)} messages ({len(message)} chars total)")
        return send_discord_bot_message(settings, message)
    return send_kakao_message_with_refresh(settings, message)


async def run_once(settings: Settings) -> None:
    print("Starting automation run...")
    print(f"Gemini profile: {settings.profile_dir}")
    print(f"Session backup: {settings.gemini_storage_state_file}")
    if settings.only_weekdays and not is_weekday():
        print("Weekend detected; skipping run.")
        return

    found = find_todays_live_video(settings)
    if not found:
        send_notification(settings, "⚠️ 오늘 라이브 영상을 찾지 못했습니다.")
        return
    video_id, video_title = found
    processed_ids = load_processed_ids(settings.processed_file)
    if video_id in processed_ids:
        print(f"Already processed video: {video_id}. Skipping.")
        return

    transcript = get_transcript_with_retry(settings, video_id)
    if not transcript:
        send_notification(settings, "⚠️ 자막 수집에 실패했습니다.")
        return

    answer = await ask_gemini_gem(settings, transcript, video_title=video_title)
    print(f"Gemini response preview: {answer[:120]}...")
    print(f"Gemini response total: {len(answer)} chars")

    response = send_notification(settings, answer)
    print(f"{settings.send_target} response status: {response.status_code}")
    if response.status_code not in (200, 201, 204):
        print(f"{settings.send_target} error body: {response.text}")
        return
    processed_ids.add(video_id)
    save_processed_ids(settings.processed_file, processed_ids)


def scheduled_job(settings: Settings) -> None:
    try:
        asyncio.run(run_once(settings))
        print("Run completed")
    except Exception as exc:  # pragma: no cover
        print(f"Run failed: {exc}")


def setup_login(settings: Settings) -> None:
    """One-time (or rare) login: browser opens, auto-detects completion, saves session backup."""

    async def _login() -> None:
        async with async_playwright() as p:
            context, page = await launch_gemini_context(
                p,
                settings,
                gem_url=settings.gemini_gem_url,
            )
            await open_gem_conversation(
                page,
                settings.gemini_gem_url,
                expected_gem_name=settings.gemini_gem_expected_name,
            )
            await save_storage_state(context, settings.gemini_storage_state_file)
            print(f"세션 저장 완료. 프로필: {settings.profile_dir}")
            print(f"백업: {settings.gemini_storage_state_file}")
            if settings.gemini_debug_hold_ms > 0:
                await page.wait_for_timeout(settings.gemini_debug_hold_ms)
            await context.close()

    asyncio.run(_login())


def main() -> None:
    settings = load_settings()

    if os.getenv("SETUP_LOGIN_ONLY", "").strip() == "1":
        setup_login(settings)
        return

    if os.getenv("RUN_ONCE", "").strip() == "1":
        print(f"RUN_ONCE mode at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        scheduled_job(settings)
        return

    schedule.every().day.at(settings.run_time).do(lambda: scheduled_job(settings))
    weekday_note = " (weekdays only in job logic)" if settings.only_weekdays else ""
    print(f"Scheduler running. Daily trigger at {settings.run_time}{weekday_note}")
    print("Press Ctrl+C to stop. For background scheduling, use register_scheduled_task.ps1")

    while True:
        schedule.run_pending()
        time.sleep(20)


if __name__ == "__main__":
    main()
