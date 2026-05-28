# personal-youtube-gemini-kakao-automation (v)

Weekday scheduled run -> today's live VOD detection -> transcript retry -> Gemini Gem automation -> KakaoTalk send.

## Flow

1. Trigger at `RUN_TIME` (default `16:00`)
2. Skip automatically on weekends (`ONLY_WEEKDAYS=true`)
3. Find today's live/VOD from `CHANNEL_URL` using `yt-dlp`
4. Retry transcript collection every 3 minutes (default max 10 tries)
5. Open Gemini Gem page with Playwright, submit transcript
6. Read Gemini response and send to Kakao memo API

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

Copy `.env.example` to `.env` and fill values:

- `CHANNEL_URL`
- `TITLE_PREFIX` (default: `[체슬리모닝브리프]`)
- `GEMINI_GEM_URL`
- `SEND_TARGET` (`discord`, `discord_bot`, or `kakao`, default `discord`)
- `DISCORD_WEBHOOK` (required when `SEND_TARGET=discord`)
- `DISCORD_BOT_TOKEN` + `DISCORD_CHANNEL_ID` (required when `SEND_TARGET=discord_bot`)
- `KAKAO_TOKEN` (optional if you use token file flow)
- `KAKAO_REST_API_KEY`
- `KAKAO_REDIRECT_URI`
- `KAKAO_TOKEN_FILE`
- `PROCESSED_FILE` (skip already sent video IDs)
- `RUN_TIME` (default `16:00`)

## Kakao token bootstrap (recommended)

1. Open authorization URL in browser:

```text
https://kauth.kakao.com/oauth/authorize?client_id=REST_API_KEY&redirect_uri=https://example.com&response_type=code&scope=talk_message
```

2. Copy `code` from redirect URL, then set `KAKAO_AUTH_CODE` in `.env`.
3. Run:

```bash
python init_kakao_token.py
```

This writes `kakao_token.json`. Main automation will refresh access token automatically.

## First login session save (required once)

This project uses Playwright persistent profile to keep Gemini login.

```bash
# PowerShell
$env:SETUP_LOGIN_ONLY="1"
python main.py
```

When browser opens:

1. Login Google/Gemini manually
2. Return to terminal and press Enter

Then reset:

```bash
$env:SETUP_LOGIN_ONLY="0"
```

## Run scheduler

```bash
python main.py
```

The script keeps running and executes every day at `RUN_TIME`.

## Key environment options

- `ONLY_WEEKDAYS=true`: run Monday-Friday only
- `TRANSCRIPT_RETRY_INTERVAL_SEC=180`: retry interval for transcript
- `TRANSCRIPT_MAX_TRIES=10`: max transcript retries
- `GEMINI_INPUT_MAX_CHARS=8000`: max transcript chars sent to Gemini
- `YT_NO_CHECK_CERTIFICATES=true`: set when `yt-dlp` fails with SSL certificate errors
- `DISABLE_SSL_VERIFY=true`: disable SSL verification for restricted environments

## Notes

- Gemini UI selector may change over time; if response read fails, update selectors in `main.py`.
- If your channel list is large, increase recent scan depth in `find_todays_live_video_id`.
- Long transcripts can exceed response timeout; increase `RESPONSE_TIMEOUT_MS`.
- Kakao message is truncated by `KAKAO_MAX_MESSAGE_LENGTH` (default 1000).
- This script automates browser interaction and may require periodic maintenance.
