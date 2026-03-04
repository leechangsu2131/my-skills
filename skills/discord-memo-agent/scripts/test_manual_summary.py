import os, requests
from dotenv import load_dotenv

load_dotenv(".env")
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

r = requests.get(
    f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages?limit=10", 
    headers={"Authorization": f"Bot {TOKEN}"},
    verify=False
)

msgs = r.json()
texts = []
for m in reversed(msgs):
    if not m.get("author", {}).get("bot") and m.get("content", "").strip():
        texts.append(m["content"])

summary = """📝 **[수동 요청] 디스코드 메모 요약 리포트** 📝

✨ **종합 요약**
- 현재 채널에는 공유된 구글 스프레드시트 링크 등 2건의 업무/참고용 링크와 일반 텍스트 2건이 등록되어 있습니다.
- 특정 일정(날짜/시간)이나 할일(체크리스트)로 명확히 분류될 만한 내용은 아직 없습니다. 

**[원본 메시지 목록]**
"""
for i, t in enumerate(texts, 1):
    summary += f"{i}. {t}\n"

chunks = [summary[i:i+1900] for i in range(0, len(summary), 1900)]
for chunk in chunks:
    payload = {
        "content": chunk,
        "username": "안티그래비티 (수동 요약)"
    }
    res = requests.post(WEBHOOK_URL, json=payload, verify=False)
    if res.status_code in (200, 204):
        print("수동 요약(청크) 전송 완료!")
    else:
        print(f"전송 실패: {res.status_code} - {res.text}")
else:
    print(f"전송 실패: {res.status_code}")
