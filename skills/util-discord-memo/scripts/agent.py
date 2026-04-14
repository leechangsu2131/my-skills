"""
Discord 메모 에이전트
====================
디스코드 입력 채널을 주기적으로 읽어 메모를 다른 채널(출력 채널)로 요약/전송하는 독립 실행 에이전트.

기능:
- Discord 입력 채널 폴링 (새 메시지 감지)
- 여러 개의 메시지를 모아 하나의 요약본으로 작성
- 일정/할일/연락처 등 특이사항 분류 및 Google Calendar 자동 등록
- 처리 결과 및 요약본을 출력 채널의 Webhook으로 알림

실행:
    python agent.py              # 폴링 모드 (5분 간격)
    python agent.py --once       # 1회 실행 후 종료
    python agent.py --read       # 최근 메시지 읽기만
"""

import os
import json
import time
import argparse
import logging
import requests
from datetime import datetime, timezone

# .env 파일 자동 로딩
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except ImportError:
    pass

# ─────────────────────────────────────────
# 설정 (환경변수 또는 .env 파일에서 로드)
# ─────────────────────────────────────────

DISCORD_BOT_TOKEN   = os.getenv("DISCORD_BOT_TOKEN", "")
DISCORD_CHANNEL_ID  = os.getenv("DISCORD_CHANNEL_ID", "1477078755951378432")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
ANTHROPIC_API_KEY   = os.getenv("ANTHROPIC_API_KEY", "")
GOOGLE_CALENDAR_ID  = os.getenv("GOOGLE_CALENDAR_ID", "primary")
POLL_INTERVAL_SEC   = int(os.getenv("POLL_INTERVAL_SEC", "300"))  # 5분

STATE_FILE = os.path.join(os.path.dirname(__file__), "agent_state.json")
DISCORD_API = "https://discord.com/api/v10"

# ─────────────────────────────────────────
# 로깅
# ─────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────
# 상태 관리 (마지막으로 처리한 메시지 ID)
# ─────────────────────────────────────────
def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_message_id": None}


def save_state(state: dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ─────────────────────────────────────────
# Discord API — 메시지 읽기 (입력 채널)
# ─────────────────────────────────────────
def fetch_messages(after_id: str = None, limit: int = 50) -> list:
    if not DISCORD_BOT_TOKEN:
        log.error("DISCORD_BOT_TOKEN이 설정되지 않았습니다. .env 파일을 확인하세요.")
        return []

    headers = {"Authorization": f"Bot {DISCORD_BOT_TOKEN}"}
    params  = {"limit": limit}
    if after_id:
        params["after"] = after_id

    url = f"{DISCORD_API}/channels/{DISCORD_CHANNEL_ID}/messages"
    resp = requests.get(url, headers=headers, params=params, timeout=10)

    if resp.status_code == 200:
        msgs = resp.json()
        return list(reversed(msgs))  # 최신순을 오래된 순으로
    elif resp.status_code == 401:
        log.error("Discord 인증 실패 — BOT TOKEN을 확인하세요.")
    elif resp.status_code == 403:
        log.error("채널 접근 권한 없음 — 봇이 해당 채널에 접근할 수 있는지 확인하세요.")
    else:
        log.error(f"Discord API 오류: {resp.status_code} {resp.text}")
    return []


# ─────────────────────────────────────────
# Discord 웹훅 — 요약본 전송 (출력 채널)
# ─────────────────────────────────────────
def send_webhook(content: str, username: str = "안티그래비티 메모 비서"):
    if not DISCORD_WEBHOOK_URL:
        log.warning("DISCORD_WEBHOOK_URL이 설정되지 않아 결과를 전송할 수 없습니다.")
        return

    payload = {"content": content, "username": username}
    try:
        resp = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        if resp.status_code in (200, 204):
            log.info("웹훅 전송 완료!")
        else:
            log.warning(f"웹훅 전송 실패: {resp.status_code}")
    except Exception as e:
        log.error(f"웹훅 오류: {e}")


# ─────────────────────────────────────────
# 분류 / 구글 캘린더 / 파이프라인
# ─────────────────────────────────────────
SYSTEM_PROMPT = """당신은 디스코드 메모를 분류하는 비서입니다.
사용자의 메모를 읽고 JSON으로 분류해 반환하세요.

출력 형식 (JSON만):
{
  "type": "schedule|todo|contact|memo|other",
  "summary": "항목 제목",
  "datetime_iso": "YYYY-MM-DDTHH:MM:SS 또는 null",
  "note": "추가 정보"
}

오늘 날짜: {today}
타임존: Asia/Seoul
"""

def classify_message(text: str) -> dict:
    if not ANTHROPIC_API_KEY:
        return rule_based_classify(text)

    today = datetime.now().strftime("%Y-%m-%d")
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    payload = {
        "model": "claude-3-haiku-20240307",
        "max_tokens": 256,
        "system": SYSTEM_PROMPT.format(today=today),
        "messages": [{"role": "user", "content": text}]
    }

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers, json=payload, timeout=15
        )
        if resp.status_code == 200:
            raw = resp.json()["content"][0]["text"].strip()
            if "```" in raw:
                raw = raw.split("```")[1].replace("json", "").strip()
            return json.loads(raw)
    except Exception as e:
        pass
    return rule_based_classify(text)

def rule_based_classify(text: str) -> dict:
    import re
    text_lower = text.lower()
    date_patterns = [r"\d{1,2}[/월]\d{1,2}", r"오전|오후", r"\d+시", r"내일|모레|다음주"]
    has_date = any(re.search(p, text_lower) for p in date_patterns)
    has_phone = bool(re.search(r"01[0-9]-?\d{4}-?\d{4}", text))

    if has_date: return {"type": "schedule", "summary": text[:50], "datetime_iso": None, "note": text}
    if has_phone: return {"type": "contact", "summary": text[:50], "datetime_iso": None, "note": text}
    if any(k in text_lower for k in ["할일", "해야", "todo", "체크"]): return {"type": "todo", "summary": text[:50], "datetime_iso": None, "note": text}
    return {"type": "memo"}

def add_to_calendar(summary: str, datetime_iso: str, description: str = "") -> bool:
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        
        creds_file = os.getenv("GOOGLE_CREDENTIALS_FILE")
        if not creds_file or not os.path.exists(creds_file): return False
        
        creds = service_account.Credentials.from_service_account_file(creds_file, scopes=["https://www.googleapis.com/auth/calendar"])
        service = build("calendar", "v3", credentials=creds)
        
        dt = datetime.fromisoformat(datetime_iso)
        end_dt = dt.replace(hour=dt.hour + 1)
        event = {
            "summary": summary, "description": description,
            "start": {"dateTime": dt.isoformat(), "timeZone": "Asia/Seoul"},
            "end":   {"dateTime": end_dt.isoformat(), "timeZone": "Asia/Seoul"},
        }
        service.events().insert(calendarId=GOOGLE_CALENDAR_ID, body=event).execute()
        return True
    except Exception as e:
        log.error(e)
    return False

def process_message(msg: dict) -> str | None:
    content = msg.get("content", "").strip()
    if not content: return None

    classified = classify_message(content)
    msg_type   = classified.get("type", "other")
    summary    = classified.get("summary", content[:50])
    dt_iso     = classified.get("datetime_iso")

    if msg_type == "schedule" and dt_iso:
        if add_to_calendar(summary, dt_iso, description=content):
            return f"📅 캘린더 등록 완료: **{summary}** ({dt_iso})"
        return f"📅 일정 감지됨: **{summary}** — 캘린더 연동 필요"
    elif msg_type == "schedule":
        return f"📅 일정/시간 감지: **{summary}** (날짜 불명확)"
    elif msg_type == "contact":
        return f"👤 연락처 감지: {summary}"
    elif msg_type == "todo":
        return f"✅ 할일 감지: {summary}"
    
    return None

# ─────────────────────────────────────────
# 폴링 루프 및 요약 생성
# ─────────────────────────────────────────
def run_once(read_only: bool = False):
    state = load_state()
    last_id = state.get("last_message_id")
    messages = fetch_messages(after_id=last_id)
    
    if not messages:
        log.info("새 메시지 없음")
        return

    log.info(f"{len(messages)}개의 새 메시지 발견")
    
    action_results = []
    raw_texts = []

    for msg in messages:
        if msg.get("author", {}).get("bot"): continue
        content = msg.get("content", "").strip()
        author = msg.get("author", {}).get("global_name") or msg.get("author", {}).get("username", "User")
        
        if read_only:
            print(f"[{author}] {content}")
        else:
            if content:
                raw_texts.append(f"- **{author}**: {content}")
                res = process_message(msg)
                if res: action_results.append(res)
        
        state["last_message_id"] = msg["id"]

    if not read_only and raw_texts:
        notification = "📝 **수집된 디스코드 메모 리포트** 📝\n\n"
        
        if action_results:
            notification += "🔔 **자동 처리 결과**\n"
            notification += "\n".join(action_results) + "\n\n"
            
        notification += "💬 **수집된 메시지 목록**\n"
        notification += "\n".join(raw_texts)
        
        send_webhook(notification)

    save_state(state)


def run_polling():
    log.info(f"폴링 시작 — 입력 채널 {DISCORD_CHANNEL_ID} (출력 웹훅 전송), {POLL_INTERVAL_SEC}초 간격")
    while True:
        try:
            run_once()
        except KeyboardInterrupt:
            break
        except Exception as e:
            log.error(f"오류: {e}")
        time.sleep(POLL_INTERVAL_SEC)


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Discord 메모 에이전트")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--read", action="store_true")
    args = parser.parse_args()

    if args.read: run_once(read_only=True)
    elif args.once: run_once()
    else: run_polling()
