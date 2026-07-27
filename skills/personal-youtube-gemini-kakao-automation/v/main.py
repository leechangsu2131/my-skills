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
    summary_save_dir: str


def bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def load_settings() -> Settings:
    load_dotenv(encoding="utf-8")

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
    summary_save_dir = resolve_data_path(
        os.getenv("SUMMARY_SAVE_DIR", "./backlog_summaries").strip(),
        SCRIPT_DIR,
    )
    save_only = bool_env("BACKLOG_SAVE_ONLY", False)
    if send_target == "discord" and not discord_webhook and not save_only:
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
        summary_save_dir=summary_save_dir,
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


BRIEF_TITLE_PREFIX_ALIASES = (
    "[체슬리모닝브리프]",
    "[모닝브리프]",
    "[Cheslie Morning Brief]",
    "[Chesley Morning Brief]",
    "[Chesly Morning Brief]",
    "[Cheslee Morning Brief]",
    "[Morning Brief]",
)

# Newer flat-playlist titles put the marker mid/end, e.g.
# "... | 박세익 전무 & 체슬리투자자문 [모닝브리프 / 26.07.16]"
BRIEF_TITLE_MARKERS = (
    "체슬리모닝브리프",
    "모닝브리프",
    "morning brief",
    "chesley morning brief",
    "cheslie morning brief",
    "chesly morning brief",
    "cheslee morning brief",
    "매일 아침 펀드매니저",
    "daily morning fund manager",
)

BRIEF_TITLE_EXCLUDE_MARKERS = (
    "별'난",
    "별난",
    "학습부장",
)


def _brief_title_prefixes(settings: Settings) -> list[str]:
    prefixes: list[str] = []
    if settings.title_prefix:
        prefixes.append(settings.title_prefix)
    for alt in BRIEF_TITLE_PREFIX_ALIASES:
        if alt not in prefixes:
            prefixes.append(alt)
    return prefixes


def _title_has_brief_prefix(title: str, prefixes: list[str]) -> bool:
    if any(title.startswith(prefix) for prefix in prefixes):
        return True
    lower = title.lower()
    if any(ex in title for ex in BRIEF_TITLE_EXCLUDE_MARKERS):
        return False
    return any(marker in lower for marker in BRIEF_TITLE_MARKERS)


def _parse_date_from_title(title: str) -> Optional[datetime.date]:
    """Parse dates embedded in titles: 26/07/16, 26.07.16, 2026-07-16, etc."""
    import re

    patterns = (
        (r"(20\d{2})[./-](\d{1,2})[./-](\d{1,2})", "ymd"),
        (r"(\d{2})[./-](\d{1,2})[./-](\d{1,2})", "ymd_short"),
        (r"(\d{1,2})[./-](\d{1,2})[./-](20\d{2})", "mdy"),
        (r"(\d{1,2})[./-](\d{1,2})[./-](\d{2})", "mdy_short"),
    )
    for pattern, kind in patterns:
        match = re.search(pattern, title)
        if not match:
            continue
        a, b, c = match.groups()
        try:
            if kind == "ymd":
                return datetime.date(int(a), int(b), int(c))
            if kind == "ymd_short":
                year = 2000 + int(a)
                return datetime.date(year, int(b), int(c))
            if kind == "mdy":
                return datetime.date(int(c), int(a), int(b))
            if kind == "mdy_short":
                year = 2000 + int(c)
                return datetime.date(year, int(a), int(b))
        except ValueError:
            continue
    return None


def _title_has_date(title: str, target: datetime.date) -> bool:
    if _parse_date_from_title(title) == target:
        return True
    patterns = (
        target.strftime("%y/%m/%d"),
        target.strftime("%Y/%m/%d"),
        target.strftime("%m/%d/%y"),
        target.strftime("%m/%d/%Y"),
        target.strftime("%y-%m-%d"),
        target.strftime("%Y-%m-%d"),
        target.strftime("%y.%m.%d"),
        target.strftime("%Y.%m.%d"),
    )
    return any(pattern in title for pattern in patterns)


def _parse_yyyymmdd(value: str) -> Optional[datetime.date]:
    raw = value.strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _upload_date_from_meta(meta: dict) -> Optional[datetime.date]:
    upload_date = str(meta.get("upload_date", "")).strip()
    if len(upload_date) == 8 and upload_date.isdigit():
        return _parse_yyyymmdd(upload_date)
    return None


def _yt_dlp_command(settings: Settings, *args: str) -> list[str]:
    command = [sys.executable, "-m", "yt_dlp"]
    if settings.yt_no_check_certificates:
        command.append("--no-check-certificates")
    command.extend(args)
    return command


def _fetch_flat_playlist(settings: Settings, playlist_suffix: str, limit: int = 20) -> list[dict]:
    command = _yt_dlp_command(
        settings,
        "--flat-playlist",
        "--dump-json",
        "--playlist-end",
        str(limit),
        settings.channel_url.rstrip("/") + playlist_suffix,
    )
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if result.returncode != 0:
        print(f"yt-dlp failed for {playlist_suffix}: {result.stderr.strip()}")
        return []

    entries: list[dict] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def _fetch_video_metadata(settings: Settings, video_id: str) -> Optional[dict]:
    command = _yt_dlp_command(
        settings,
        "--dump-json",
        "--skip-download",
        f"https://www.youtube.com/watch?v={video_id}",
    )
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def find_todays_live_video(settings: Settings) -> Optional[tuple[str, str]]:
    return find_live_video_for_date(settings, datetime.date.today())


def find_live_video_for_date(settings: Settings, target_date: datetime.date) -> Optional[tuple[str, str]]:
    target_yyyymmdd = target_date.strftime("%Y%m%d")
    prefixes = _brief_title_prefixes(settings)

    for playlist_suffix in ("/streams", "/videos"):
        entries = _fetch_flat_playlist(settings, playlist_suffix, limit=50)
        for video in entries:
            title = str(video.get("title", ""))
            video_id = str(video.get("id", "")).strip()
            if not video_id:
                continue
            if _title_has_brief_prefix(title, prefixes) and _title_has_date(title, target_date):
                print(f"Found live VOD for {target_date}: {title} / {video_id}")
                return video_id, title

        for video in entries[:20]:
            video_id = str(video.get("id", "")).strip()
            if not video_id:
                continue
            meta = _fetch_video_metadata(settings, video_id)
            if not meta:
                continue
            upload_date = str(meta.get("upload_date", ""))
            title = str(meta.get("title", ""))
            if upload_date == target_yyyymmdd and _title_has_brief_prefix(title, prefixes):
                print(f"Found live VOD for {target_date} (metadata): {title} / {video_id}")
                return video_id, title

    return None


def find_todays_live_video_id(settings: Settings) -> Optional[str]:
    found = find_todays_live_video(settings)
    return found[0] if found else None


def collect_backlog_targets(
    settings: Settings,
    from_date: datetime.date,
    to_date: datetime.date,
    processed_ids: set[str],
    include_weekends: bool = True,
) -> list[tuple[datetime.date, str, str]]:
    """Return [(upload_date, video_id, title), ...] oldest first.

    Prefer date-in-title matching to avoid slow per-video metadata fetches.
    For /streams flat English titles without markers, resolve metadata for recent items.
    """
    prefixes = _brief_title_prefixes(settings)
    seen_ids: set[str] = set()
    candidates: list[tuple[datetime.date, str, str]] = []
    force = bool_env("BACKLOG_FORCE", False)
    skip_existing = bool_env("BACKLOG_SKIP_EXISTING_SUMMARY", True)

    def consider(video_id: str, title: str, upload: Optional[datetime.date]) -> None:
        if not upload:
            return
        if upload < from_date or upload > to_date:
            return
        if not include_weekends and upload.weekday() >= 5:
            return
        if not force and video_id in processed_ids:
            return
        if skip_existing:
            summary_path = os.path.join(
                settings.summary_save_dir,
                f"{upload.isoformat()}_{video_id}.md",
            )
            if os.path.exists(summary_path) and os.path.getsize(summary_path) > 400:
                print(f"Skip existing summary: {summary_path}")
                return
        candidates.append((upload, video_id, title))

    for playlist_suffix in ("/streams", "/videos"):
        entries = _fetch_flat_playlist(settings, playlist_suffix, limit=100)
        for index, video in enumerate(entries):
            video_id = str(video.get("id", "")).strip()
            if not video_id or video_id in seen_ids:
                continue
            title = str(video.get("title", ""))
            matched = _title_has_brief_prefix(title, prefixes)
            # Recent /streams items may be English flat titles without markers.
            maybe_resolve = (
                playlist_suffix == "/streams"
                and not matched
                and index < 35
                and not any(ex in title for ex in BRIEF_TITLE_EXCLUDE_MARKERS)
            )
            if not matched and not maybe_resolve:
                continue

            upload = _parse_date_from_title(title)
            resolved_title = title
            if not matched or not upload:
                meta = _fetch_video_metadata(settings, video_id) or {}
                resolved_title = str(meta.get("title", title))
                if not _title_has_brief_prefix(resolved_title, prefixes):
                    continue
                upload = upload or _upload_date_from_meta(meta) or _parse_date_from_title(resolved_title)

            seen_ids.add(video_id)
            consider(video_id, resolved_title, upload)

    deduped: dict[str, tuple[datetime.date, str, str]] = {}
    for item in candidates:
        deduped[item[1]] = item
    return sorted(deduped.values(), key=lambda row: row[0])


def save_summary_file(settings: Settings, upload_date: datetime.date, video_id: str, title: str, summary: str) -> str:
    os.makedirs(settings.summary_save_dir, exist_ok=True)
    filename = f"{upload_date.isoformat()}_{video_id}.md"
    path = os.path.join(settings.summary_save_dir, filename)
    body = summary.strip()
    for noise in ("Gemini said", "Gemini의 응답", "Gemini 응답"):
        if body.startswith(noise):
            body = body[len(noise):].lstrip("\n: ").strip()
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n")
        f.write(f"- 날짜: {upload_date.isoformat()}\n")
        f.write(f"- video_id: {video_id}\n")
        f.write(f"- url: https://www.youtube.com/watch?v={video_id}\n\n")
        f.write(body)
        f.write("\n")
    print(f"Saved summary: {path}")
    return path


async def get_youtube_transcript(video_id: str, languages: list[str]) -> str:
    api = YouTubeTranscriptApi()
    fetched = api.fetch(video_id, languages=languages)
    return " ".join(snippet.text.strip() for snippet in fetched if snippet.text)


def _vtt_to_text(path: str) -> str:
    """Convert VTT/SRT to plain text; strip cue tags and prefer clean cue text."""
    import re

    lines: list[str] = []
    seen: set[str] = set()
    tag_re = re.compile(r"<[^>]+>")
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.strip()
            if (
                not line
                or line == "WEBVTT"
                or "-->" in line
                or line.isdigit()
                or line.startswith("NOTE")
                or line.startswith("Kind:")
                or line.startswith("Language:")
            ):
                continue
            # Drop inline timing/style tags: <00:00:13.000><c> ...
            cleaned = tag_re.sub("", line).strip()
            if not cleaned:
                continue
            if cleaned in seen:
                continue
            seen.add(cleaned)
            lines.append(cleaned)
    return " ".join(lines)


def get_transcript_via_ytdlp(settings: Settings, video_id: str) -> Optional[str]:
    tmp_dir = os.path.join(SCRIPT_DIR, ".transcript_cache")
    os.makedirs(tmp_dir, exist_ok=True)
    # Prefer Korean auto/manual subs first; en as fallback only.
    # Fetch ko alone first to avoid 429 when requesting multiple langs.
    for langs in ("ko", "en"):
        output_tpl = os.path.join(tmp_dir, f"{video_id}.%(ext)s")
        ko_path = os.path.join(tmp_dir, f"{video_id}.ko.vtt")
        if langs == "en" and os.path.exists(ko_path) and os.path.getsize(ko_path) > 1000:
            break
        command = _yt_dlp_command(
            settings,
            "--write-auto-sub",
            "--write-sub",
            "--sub-lang",
            langs,
            "--skip-download",
            "--no-overwrites",
            "-o",
            output_tpl,
            f"https://www.youtube.com/watch?v={video_id}",
        )
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="ignore")
        if result.returncode != 0:
            print(f"yt-dlp subtitle ({langs}) returned {result.returncode} for {video_id}; checking local files.")

    # Prefer language order from settings (ko before en), not longest file.
    ordered_paths: list[str] = []
    for lang in settings.language_priority + ["ko", "en"]:
        for suffix in (f".{lang}.vtt", f".{lang}.srt"):
            path = os.path.join(tmp_dir, f"{video_id}{suffix}")
            if os.path.exists(path) and path not in ordered_paths:
                ordered_paths.append(path)

    best = ""
    best_path = ""
    for path in ordered_paths:
        text = _vtt_to_text(path)
        # Prefer first language in priority that has enough text.
        if len(text) >= 400:
            print(f"Transcript collected via yt-dlp ({os.path.basename(path)}): {len(text)} chars")
            return text
        if len(text) > len(best):
            best = text
            best_path = path
    if best:
        print(f"Transcript collected via yt-dlp ({os.path.basename(best_path)}): {len(best)} chars")
    return best or None


def get_transcript_with_retry(settings: Settings, video_id: str) -> Optional[str]:
    # Prefer yt-dlp first when TRANSCRIPT_PREFER_YTDLP=1 (API often blocked).
    prefer_ytdlp = bool_env("TRANSCRIPT_PREFER_YTDLP", True)
    if prefer_ytdlp:
        fallback = get_transcript_via_ytdlp(settings, video_id)
        if fallback:
            return fallback

    api_failures = 0
    max_api_tries = min(settings.transcript_max_tries, 2)
    for attempt in range(max_api_tries):
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
            api_failures += 1
            remaining = max_api_tries - attempt - 1
            print(
                f"Transcript API not ready ({attempt + 1}/{max_api_tries}): {exc}. "
                f"Remaining retries: {remaining}"
            )
        if attempt < max_api_tries - 1:
            time.sleep(min(settings.transcript_retry_interval_sec, 5))

    return get_transcript_via_ytdlp(settings, video_id)


RESPONSE_SELECTORS = (
    "message-content",
    "model-response",
    '[data-message-author-role="model"]',
    ".model-response-text",
    '[data-test-id="message-content"]',
)


async def _latest_response_locator(page):
    for selector in RESPONSE_SELECTORS:
        responses = page.locator(selector)
        count = await responses.count()
        if count > 0:
            return responses.nth(count - 1)
    return None


async def _latest_response_text(page) -> str:
    last = await _latest_response_locator(page)
    if not last:
        return ""
    try:
        return (await last.inner_text()).strip()
    except Exception:
        return ""


async def _best_response_text(page, previous_last_text: str = "") -> str:
    best = ""
    for selector in RESPONSE_SELECTORS:
        responses = page.locator(selector)
        count = await responses.count()
        for index in range(count):
            try:
                node = responses.nth(index)
                text = (await node.inner_text()).strip()
                if not text or text == previous_last_text:
                    continue
                if len(text) > len(best):
                    best = text
            except Exception:
                continue
    return best


async def _extract_response_fallback(page, prompt_text: str) -> str:
    try:
        body = await page.locator("main, .chat-history, body").first.inner_text(timeout=10000)
    except Exception:
        return ""

    marker = "전체 스크립트입니다:"
    if marker not in body:
        return ""

    tail = body.split(marker)[-1].strip()
    prompt_tail = prompt_text[-800:].strip()
    if prompt_tail and prompt_tail in tail:
        tail = tail.split(prompt_tail, 1)[-1].strip()
    elif len(tail) > len(prompt_text):
        tail = tail[len(prompt_text) :].strip()
    return tail


async def _generation_in_progress(page) -> bool:
    stop_button = page.locator(
        "button[aria-label*='중지'], button[aria-label*='Stop'], "
        "[data-is-loading='true'], .loading"
    )
    return await stop_button.count() > 0


async def wait_for_gemini_response(
    page,
    previous_count: int,
    timeout_ms: int,
    previous_last_text: str = "",
    prompt_text: str = "",
) -> str:
    start = time.time()
    generation_started = False
    responses = page.locator(", ".join(RESPONSE_SELECTORS))

    while (time.time() - start) * 1000 < timeout_ms:
        latest_count = await responses.count()
        latest_text = await _latest_response_text(page)
        if latest_count > previous_count:
            generation_started = True
            break
        if latest_text and latest_text != previous_last_text:
            if len(latest_text) > len(previous_last_text) + 20:
                generation_started = True
                break
        if await _generation_in_progress(page):
            generation_started = True
            break
        await page.wait_for_timeout(800)

    if not generation_started:
        raise RuntimeError("No new Gemini response detected after sending prompt.")

    settle_deadline = time.time() + min(180, timeout_ms / 1000)
    prev_len = 0
    stable_rounds = 0
    text = ""
    while time.time() < settle_deadline:
        still_generating = await _generation_in_progress(page)
        text = await _best_response_text(page, previous_last_text=previous_last_text)
        if not text:
            await page.wait_for_timeout(1000)
            continue
        if not still_generating and len(text) == prev_len and len(text) > 0:
            stable_rounds += 1
            if stable_rounds >= 3:
                break
        else:
            stable_rounds = 0
            prev_len = len(text)
        await page.wait_for_timeout(1500)

    if (not text or text == previous_last_text) and prompt_text:
        fallback = await _extract_response_fallback(page, prompt_text)
        if len(fallback) >= 400 and len(fallback) > len(text):
            print(f"Using chat body fallback for Gemini response ({len(fallback)} chars).")
            text = fallback

    if not text or text == previous_last_text:
        await page.screenshot(path=os.path.join(SCRIPT_DIR, "debug_empty_response.png"), full_page=True)
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
        "rich-textarea .ql-editor",
        "rich-textarea div[contenteditable='true']",
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


async def _input_box_text(input_box) -> str:
    try:
        return (await input_box.inner_text()).strip()
    except Exception:
        return ""


async def _clear_input_box(page, input_box) -> None:
    await input_box.click()
    await page.keyboard.press("Control+a")
    await page.keyboard.press("Delete")
    await page.wait_for_timeout(200)


async def _start_new_gem_chat(page, gem_url: str) -> None:
    selectors = [
        'button[aria-label*="New chat"]',
        'button[aria-label*="새 채팅"]',
        'button:has-text("새 채팅")',
    ]
    for sel in selectors:
        btn = page.locator(sel).first
        if await btn.count() == 0:
            continue
        try:
            await btn.click(timeout=2000)
            await page.wait_for_timeout(1500)
            print("Started a new Gemini chat.")
            return
        except Exception:
            continue
    await page.goto(gem_url, wait_until="load", timeout=60000)
    await page.wait_for_timeout(2500)
    print("Reloaded Gem URL for a fresh chat.")


async def _fill_prompt_text(page, input_box, prompt_text: str) -> None:
    await input_box.click()
    await _clear_input_box(page, input_box)

    filled_len = await page.evaluate(
        """(value) => {
            const editor = document.querySelector('rich-textarea .ql-editor')
                || document.querySelector('rich-textarea [contenteditable="true"]')
                || document.querySelector('div[contenteditable="true"]:not(.ql-clipboard)');
            if (!editor) return 0;
            editor.focus();
            editor.textContent = value;
            editor.dispatchEvent(new InputEvent('input', { bubbles: true }));
            editor.dispatchEvent(new Event('change', { bubbles: true }));
            return (editor.innerText || editor.textContent || '').length;
        }""",
        prompt_text,
    )
    await page.wait_for_timeout(1000)
    print(f"JS editor fill reported: {filled_len} chars")

    if max(filled_len, len(await _input_box_text(input_box))) < 50:
        print("JS fill looks empty; trying insert_text.")
        await _clear_input_box(page, input_box)
        await page.keyboard.insert_text(prompt_text)
        await page.wait_for_timeout(1000)

    if len(await _input_box_text(input_box)) < 50:
        print("insert_text looks empty; trying clipboard paste.")
        await _clear_input_box(page, input_box)
        try:
            await page.context.grant_permissions(["clipboard-read", "clipboard-write"])
            await page.evaluate("(value) => navigator.clipboard.writeText(value)", prompt_text)
            await page.keyboard.press("Control+v")
            await page.wait_for_timeout(800)
            await page.keyboard.press("Space")
            await page.wait_for_timeout(300)
        except Exception as exc:
            print(f"Clipboard paste failed: {exc}")


async def _submit_prompt(page) -> None:
    send_selectors = [
        "button[aria-label*='전송']",
        "button[aria-label*='Send']",
        "[data-test-id='send-button']",
        "button[mattooltip*='전송']",
        "button[mattooltip*='Send']",
    ]
    for sel in send_selectors:
        send_btn = page.locator(sel).first
        if await send_btn.count() == 0:
            continue
        try:
            if await send_btn.is_enabled():
                await send_btn.click(timeout=2000)
                await page.wait_for_timeout(700)
                return
        except Exception:
            continue

    await page.keyboard.press("Enter")
    await page.wait_for_timeout(700)
    for sel in send_selectors:
        send_btn = page.locator(sel).first
        if await send_btn.count() == 0:
            continue
        try:
            await send_btn.click(timeout=1500, force=True)
        except Exception:
            pass


async def _wait_for_generation_start(page, timeout_ms: int) -> bool:
    deadline = time.time() + timeout_ms / 1000
    responses = page.locator(", ".join(RESPONSE_SELECTORS))
    initial_count = await responses.count()
    initial_text = await _best_response_text(page)

    while time.time() < deadline:
        if await _generation_in_progress(page):
            return True
        if await responses.count() > initial_count:
            return True
        latest_text = await _best_response_text(page)
        if latest_text and latest_text != initial_text and len(latest_text) > len(initial_text) + 20:
            return True
        await page.wait_for_timeout(1000)
    return False


async def _run_gemini_prompt(
    page,
    settings: Settings,
    text: str,
    video_title: str,
    gem_url: str = "",
) -> str:
    # Always start a fresh chat so backlog items do not bleed into each other.
    if gem_url:
        await _start_new_gem_chat(page, gem_url)

    if settings.gemini_force_pro:
        await _select_gemini_pro(page)

    await page.wait_for_selector(
        "rich-textarea, div[contenteditable='true'], textarea",
        timeout=30000,
    )
    prompt_text = build_gem_prompt(
        text[: settings.gemini_input_max_chars],
        video_title or "체슬리모닝브리프",
        settings.gemini_use_gem_prompt,
    )
    input_box = await _find_input_box(page)

    last_error: Optional[Exception] = None
    for send_attempt in range(2):
        if send_attempt > 0:
            print("Gemini send retry: re-filling prompt and submitting again.")
            if gem_url:
                await _start_new_gem_chat(page, gem_url)
                if settings.gemini_force_pro:
                    await _select_gemini_pro(page)
                input_box = await _find_input_box(page)

        response_nodes = page.locator(", ".join(RESPONSE_SELECTORS))
        previous_count = await response_nodes.count()
        previous_last_text = await _latest_response_text(page)

        await _fill_prompt_text(page, input_box, prompt_text)
        filled_len = len(await _input_box_text(input_box))
        print(f"Prompt filled in input box: {filled_len} chars")
        if filled_len < 50:
            raise RuntimeError("Gemini prompt was not inserted into the input box.")

        await _submit_prompt(page)
        if not await _wait_for_generation_start(page, timeout_ms=90000):
            print("Gemini generation did not start after submit.")
            await page.screenshot(path=os.path.join(SCRIPT_DIR, f"debug_not_started_{send_attempt}.png"), full_page=True)
            last_error = RuntimeError("No new Gemini response detected after sending prompt.")
            if send_attempt == 0:
                continue
            raise last_error

        try:
            result = await wait_for_gemini_response(
                page,
                previous_count=previous_count,
                timeout_ms=settings.response_timeout_ms,
                previous_last_text=previous_last_text,
                prompt_text=prompt_text,
            )
            validate_gemini_response(result, settings.gemini_min_response_chars)
            return result
        except RuntimeError as exc:
            last_error = exc
            retryable = (
                "No new Gemini response detected" in str(exc)
                or "Gemini response was empty" in str(exc)
            )
            if retryable and send_attempt == 0:
                continue
            raise

    if last_error:
        raise last_error
    raise RuntimeError("Gemini prompt submission failed.")


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
                    result = await _run_gemini_prompt(
                        page,
                        settings,
                        text,
                        video_title,
                        gem_url=settings.gemini_gem_url,
                    )
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


def send_notification(settings: Settings, message: str):
    if settings.send_target == "discord":
        if not settings.discord_webhook:
            print("Discord webhook not set; skipping remote send.")
            return type("Resp", (), {"status_code": 204, "text": ""})()
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


async def process_video(
    settings: Settings,
    video_id: str,
    video_title: str,
    processed_ids: set[str],
    upload_date: Optional[datetime.date] = None,
    persist_processed: bool = True,
) -> bool:
    force = bool_env("BACKLOG_FORCE", False)
    if video_id in processed_ids and not force:
        print(f"Already processed video: {video_id}. Skipping.")
        return False
    if force and video_id in processed_ids:
        print(f"BACKLOG_FORCE: reprocessing {video_id}")

    transcript = get_transcript_with_retry(settings, video_id)
    if not transcript:
        send_notification(settings, f"⚠️ 자막 수집에 실패했습니다. ({video_title})")
        return False

    answer = await ask_gemini_gem(settings, transcript, video_title=video_title)
    print(f"Gemini response preview: {answer[:120]}...")
    print(f"Gemini response total: {len(answer)} chars")

    header_bits = []
    if upload_date:
        header_bits.append(upload_date.isoformat())
    if video_title:
        header_bits.append(video_title)
    header = " | ".join(header_bits)
    payload = f"**{header}**\n\n{answer}" if header else answer

    if upload_date:
        save_summary_file(settings, upload_date, video_id, video_title, answer)

    response = send_notification(settings, payload)
    if settings.send_target == "discord" and settings.discord_webhook:
        print(f"{settings.send_target} response status: {response.status_code}")
        if response.status_code not in (200, 201, 204):
            print(f"{settings.send_target} error body: {response.text}")
            return False
    elif settings.send_target not in ("discord",):
        print(f"{settings.send_target} response status: {response.status_code}")
        if response.status_code not in (200, 201, 204):
            print(f"{settings.send_target} error body: {response.text}")
            return False

    if persist_processed:
        processed_ids.add(video_id)
        save_processed_ids(settings.processed_file, processed_ids)
    return True


async def run_once(settings: Settings) -> None:
    print("Starting automation run...")
    print(f"Gemini profile: {settings.profile_dir}")
    print(f"Session backup: {settings.gemini_storage_state_file}")
    if settings.only_weekdays and not is_weekday() and not os.getenv("FORCE_VIDEO_ID"):
        print("Weekend detected; skipping run.")
        return

    force_video_id = os.getenv("FORCE_VIDEO_ID", "").strip()
    if force_video_id:
        print(f"Using forced video ID: {force_video_id}")
        video_id = force_video_id
        video_title = "체슬리모닝브리프 (Forced Test)"
        processed_ids: set[str] = set()
        await process_video(settings, video_id, video_title, processed_ids, persist_processed=False)
        return

    found = find_todays_live_video(settings)
    if not found:
        send_notification(settings, "⚠️ 오늘 라이브 영상을 찾지 못했습니다.")
        return
    video_id, video_title = found
    processed_ids = load_processed_ids(settings.processed_file)
    await process_video(
        settings,
        video_id,
        video_title,
        processed_ids,
        upload_date=datetime.date.today(),
    )


async def run_backlog(settings: Settings) -> None:
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)

    from_date = _parse_yyyymmdd(os.getenv("BACKLOG_FROM", "")) or (today - datetime.timedelta(days=7))
    to_date = _parse_yyyymmdd(os.getenv("BACKLOG_TO", "")) or yesterday
    if from_date > to_date:
        raise ValueError(f"BACKLOG_FROM ({from_date}) must be <= BACKLOG_TO ({to_date})")

    include_weekends = bool_env("BACKLOG_INCLUDE_WEEKENDS", True)
    processed_ids = load_processed_ids(settings.processed_file)
    targets = collect_backlog_targets(
        settings,
        from_date,
        to_date,
        processed_ids,
        include_weekends=include_weekends,
    )

    if not targets:
        print(f"No backlog videos between {from_date} and {to_date}.")
        return

    limit_raw = os.getenv("BACKLOG_LIMIT", "").strip()
    limit = int(limit_raw) if limit_raw.isdigit() and int(limit_raw) > 0 else 0
    if limit:
        targets = targets[:limit]
        print(f"Backlog limited to first {limit} video(s)")

    stop_on_error = bool_env("BACKLOG_STOP_ON_ERROR", True)
    print(f"Backlog: {len(targets)} video(s) from {from_date} to {to_date} (stop_on_error={stop_on_error})")
    for upload_date, video_id, title in targets:
        print(f"\n=== Backlog {upload_date} / {video_id} ===")
        print(f"Title: {title}")
        try:
            ok = await process_video(
                settings,
                video_id,
                title,
                processed_ids,
                upload_date=upload_date,
            )
            if not ok:
                print(f"Backlog item failed or skipped: {upload_date} / {video_id}")
                if stop_on_error:
                    raise RuntimeError(f"Backlog stopped after failure: {upload_date} / {video_id}")
        except Exception as exc:
            print(f"Backlog item error ({upload_date} / {video_id}): {exc}")
            if stop_on_error:
                raise


def scheduled_job(settings: Settings) -> None:
    try:
        if os.getenv("RUN_BACKLOG", "").strip() == "1":
            asyncio.run(run_backlog(settings))
        else:
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

    if os.getenv("RUN_ONCE", "").strip() == "1" or os.getenv("RUN_BACKLOG", "").strip() == "1":
        mode = "BACKLOG" if os.getenv("RUN_BACKLOG", "").strip() == "1" else "RUN_ONCE"
        print(f"{mode} mode at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
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
