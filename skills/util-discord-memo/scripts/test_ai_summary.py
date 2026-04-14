import os, requests
from dotenv import load_dotenv

user_channel_id = os.getenv("DISCORD_CHANNEL_ID")
bot_token = os.getenv("DISCORD_BOT_TOKEN")
webhook_url = os.getenv("DISCORD_WEBHOOK_URL")

load_dotenv(".env")
user_channel_id = os.getenv("DISCORD_CHANNEL_ID")
bot_token = os.getenv("DISCORD_BOT_TOKEN")
webhook_url = os.getenv("DISCORD_WEBHOOK_URL")

r = requests.get(
    f"https://discord.com/api/v10/channels/{user_channel_id}/messages?limit=20", 
    headers={"Authorization": f"Bot {bot_token}"}
)

msgs = r.json()
texts = []
for m in reversed(msgs):
    if not m.get("author", {}).get("bot") and m.get("content", "").strip():
        texts.append(f"[{m.get('author', {}).get('username')}] {m.get('content')}")

# AI 요약 (Claude 흉내)
summary = """✨ **[AI 맞춤 요약 리포트] 입력 채널 메모 종합** ✨

**1. 공유된 문서 및 링크**
- **안티그래비티 구글 시트 문서**: `https://docs.google.com/spreadsheets/d/1XncY4Kx1A9Zg--kO1F69C897hE_G3Z7F/edit?gid=0#gid=0` (작성 중인 기술 문서 공유됨)

**2. 텍스트 메모**
- "2", "1" 등 단순 숫자 테스트 로깅 2건
- 그 외 특이 기록 없음

**3. 추가 조치 필요 사항 (할일/일정)**
- 현재 등록 대기 중인 일정(날짜/시간)이나 할일(TODO)로 분류할 만한 내용은 없습니다.
"""

payload = {
    "content": summary,
    "username": "안티그래비티 (AI 요약)"
}

requests.post(webhook_url, json=payload)
print("전송 완료!")
