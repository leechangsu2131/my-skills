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


def bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def load_settings() -> Settings:
    load_dotenv()

    channel_url = os.getenv("CHANNEL_URL", "").strip()
    title_prefix = os.getenv("TITLE_PREFIX", "[체슬리모닝브리프]").strip()
    gemini_gem_url = os.getenv("GEMINI_GEM_URL", "").strip()
    send_target = os.getenv("SEND_TARGET", "discord").strip().lower()
    discord_webhook = os.getenv("DISCORD_WEBHOOK", "").strip()
    discord_bot_token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
    discord_channel_id = os.getenv("DISCORD_CHANNEL_ID", "").strip()
    kakao_token = os.getenv("KAKAO_TOKEN", "").strip()
    kakao_rest_api_key = os.getenv("KAKAO_REST_API_KEY", "").strip()
    kakao_redirect_uri = os.getenv("KAKAO_REDIRECT_URI", "https://example.com").strip()
    kakao_token_file = os.getenv("KAKAO_TOKEN_FILE", "./kakao_token.json").strip()
    processed_file = os.getenv("PROCESSED_FILE", "./processed.json").strip()
    run_time = os.getenv("RUN_TIME", "16:00").strip()
    profile_dir = os.getenv("PLAYWRIGHT_PROFILE_DIR", "./chrome_profile").strip()

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
    )


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


def find_todays_live_video_id(settings: Settings) -> Optional[str]:
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
            return video_id

    return None


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

    # Additional settling wait: some Gemini UIs keep streaming for a while.
    settle_deadline = time.time() + min(45, timeout_ms / 1000)
    while time.time() < settle_deadline:
        stop_button = page.locator(
            "button[aria-label*='중지'], button[aria-label*='Stop'], "
            "[data-is-loading='true'], .loading"
        )
        if await stop_button.count() == 0:
            break
        await page.wait_for_timeout(1000)

    last = responses.nth(latest_count - 1)
    await last.wait_for(state="visible", timeout=timeout_ms)
    await page.wait_for_timeout(1500)
    text = (await last.inner_text()).strip()
    if not text:
        raise RuntimeError("Gemini response was empty.")
    return text


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


async def ask_gemini_gem(settings: Settings, text: str) -> str:
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=settings.profile_dir,
            headless=settings.headless,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = await context.new_page()

        try:
            await page.goto(settings.gemini_gem_url, wait_until="domcontentloaded")
            await page.wait_for_selector(
                "rich-textarea, div[contenteditable='true'], textarea",
                timeout=30000,
            )
            response_nodes = page.locator("message-content, model-response")
            previous_count = await response_nodes.count()

            input_box = await _find_input_box(page)
            await input_box.click()
            prompt_text = text[: settings.gemini_input_max_chars]

            # Prefer direct fill; fall back to clipboard paste for long text robustness.
            try:
                await input_box.fill("")
                await input_box.fill(prompt_text)
            except Exception:
                await page.evaluate(
                    "(value) => navigator.clipboard.writeText(value)",
                    prompt_text,
                )
                await page.keyboard.press("Control+a")
                await page.keyboard.press("Delete")
                await page.keyboard.press("Control+v")

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

            return await wait_for_gemini_response(
                page,
                previous_count=previous_count,
                timeout_ms=settings.response_timeout_ms,
            )
        except PlaywrightTimeoutError as exc:
            raise RuntimeError("Timed out while waiting for Gemini UI or response.") from exc
        finally:
            if settings.gemini_debug_hold_ms > 0:
                print(f"Holding browser for debug: {settings.gemini_debug_hold_ms}ms")
                await page.wait_for_timeout(settings.gemini_debug_hold_ms)
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


def send_discord_message(settings: Settings, message: str) -> requests.Response:
    payload = {"content": message[:1900]}
    return requests.post(
        settings.discord_webhook,
        json=payload,
        timeout=20,
        verify=_request_verify_ssl(settings),
    )


def send_discord_bot_message(settings: Settings, message: str) -> requests.Response:
    endpoint = f"https://discord.com/api/v10/channels/{settings.discord_channel_id}/messages"
    headers = {
        "Authorization": f"Bot {settings.discord_bot_token}",
        "Content-Type": "application/json",
    }
    payload = {"content": message[:1900]}
    return requests.post(
        endpoint,
        headers=headers,
        json=payload,
        timeout=20,
        verify=_request_verify_ssl(settings),
    )


def send_notification(settings: Settings, message: str) -> requests.Response:
    if settings.send_target == "discord":
        return send_discord_message(settings, message)
    if settings.send_target == "discord_bot":
        return send_discord_bot_message(settings, message)
    return send_kakao_message_with_refresh(settings, message)


async def run_once(settings: Settings) -> None:
    print("Starting automation run...")
    if settings.only_weekdays and not is_weekday():
        print("Weekend detected; skipping run.")
        return

    video_id = find_todays_live_video_id(settings)
    if not video_id:
        send_notification(settings, "⚠️ 오늘 라이브 영상을 찾지 못했습니다.")
        return
    processed_ids = load_processed_ids(settings.processed_file)
    if video_id in processed_ids:
        print(f"Already processed video: {video_id}. Skipping.")
        return

    transcript = get_transcript_with_retry(settings, video_id)
    if not transcript:
        send_notification(settings, "⚠️ 자막 수집에 실패했습니다.")
        return

    answer = await ask_gemini_gem(settings, transcript)
    print(f"Gemini response preview: {answer[:120]}...")

    response = send_notification(settings, answer)
    print(f"{settings.send_target} response status: {response.status_code}")
    if response.status_code != 200:
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


def setup_login(profile_dir: str, headless: bool = False) -> None:
    async def _login() -> None:
        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=profile_dir,
                headless=headless,
                channel="chrome",
            )
            page = await context.new_page()
            await page.goto("https://gemini.google.com", wait_until="domcontentloaded")
            print("Please complete Google/Gemini login in the opened browser.")
            input("After login completes, press Enter here to close browser...")
            await context.close()

    asyncio.run(_login())


def main() -> None:
    settings = load_settings()

    if os.getenv("SETUP_LOGIN_ONLY", "").strip() == "1":
        setup_login(profile_dir=settings.profile_dir, headless=False)
        return

    schedule.every().day.at(settings.run_time).do(lambda: scheduled_job(settings))
    print(f"Waiting for scheduled run at {settings.run_time} every day...")

    while True:
        schedule.run_pending()
        time.sleep(20)


if __name__ == "__main__":
    main()
