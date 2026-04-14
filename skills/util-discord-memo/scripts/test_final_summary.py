import os, requests
from dotenv import load_dotenv

load_dotenv(".env")
webhook_url = os.getenv("DISCORD_WEBHOOK_URL")

summary = """📣 **[업무 공지 및 요약] 학교 업무 (안티그래비티 어썸 스킬 개발 건)**

현재 업무 채널에 공유된 주요 진행 사항과 참고 자료입니다.

📌 **주요 진행 현황**
- **문서 공유**: [안티그래비티-어썸-스킬 작업 시트](https://docs.google.com/spreadsheets/d/1XncY4Kx1A9Zg--kO1F69C897hE_G3Z7F/edit)가 공유되었습니다.
- **요청 사항**: 해당 구글 스프레드시트에 기재된 '생성 내용'을 업무에 적극 참고하여 주시기 바랍니다.

현재 시점 기준으로, 이 외에 긴급하게 추가된 일정이나 할 일은 없습니다. 공유된 구글 시트 내용을 먼저 우선적으로 검토해 주시기 바랍니다.
"""

payload = {
    "content": summary,
    "username": "안티그래비티 (업무 요약 비서)"
}

requests.post(webhook_url, json=payload)
print("업무 공지 발송 완료")
