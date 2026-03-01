import os, requests
from dotenv import load_dotenv

load_dotenv(".env")
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

r = requests.get(
    f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages?limit=10", 
    headers={"Authorization": f"Bot {TOKEN}"}
)

msgs = r.json()
texts = []
# 과거 메시지부터 순서대로
for m in reversed(msgs):
    if not m.get("author", {}).get("bot"):
        content = m.get("content", "").strip()
        author = m.get("author", {}).get("global_name") or m.get("author", {}).get("username", "User")
        if content:
            texts.append(f"- **{author}**: {content}")

if not texts:
    summary_text = "🚫 읽어올 메시지가 없습니다."
else:
    summary_text = "📝 **수집된 메모 요약 리포트** (테스트 발송)\n\n"
    summary_text += "\n".join(texts)
    summary_text += "\n\n💡 *이 결과는 입력 채널에서 메시지를 모아 출력 채널로 보내는 기능의 테스트입니다.*"

payload = {
    "content": summary_text,
    "username": "AI 메모 요약 비서"
}

res = requests.post(WEBHOOK_URL, json=payload)
if res.status_code in (200, 204):
    print("웹훅 전송 성공!")
else:
    print(f"웹훅 전송 실패: {res.status_code} {res.text}")
