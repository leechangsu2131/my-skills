import os, requests
from dotenv import load_dotenv

load_dotenv(".env")
webhook_url = os.getenv("DISCORD_WEBHOOK_URL")

summary = """📣 **[안티그래비티 요약 비서] 화천초등학교 업무 공지 및 종합 사항**

채널에 올라온 메시지들을 분석하여 교무/행정 업무 중심으로 정리한 요약본입니다.

📌 **요청 및 협조 사항**
- **교과서 현황 자료 작성**: 학년 대표 선생님들께서는 학교 공유 스프레드시트에 교과서 현황 자료를 작성해 주시기 바랍니다. (4학년 작성 내용 참고)
  🔗 [교과서 현황 구글 시트 링크](https://docs.google.com/spreadsheets/d/1O2aKSYPX6A59UXgpwCK-NyoczxLs9WfHcDeVVM2Kl30/edit?gid=0#gid=0)

💡 **행정/운영 공지 및 건의 사항**
- **물품 구입 안내 (경주 에스디피)**
  - '경주 에스디피' 방문 시 "화천초등학교 장부"로 말씀하시고 물품 수령 가능.
  - 수령 시 학습준비물인지 환경구성물품인지 구분을 명확히 하여, 추후 담당자가 품의를 올릴 수 있게 전달 요망.
  - *예산 참고: 환경구성물품은 1년에 학급당 11만 원 배정 (총 초등 13학급, 특수 1학급)*
- **신발장/사물함 라벨링 개선 건의**
  - 각 교실의 신발장과 사물함에 학생 이름 대신 **통일된 번호**만 부착하여, 매년 새로 붙일 필요 없이 반영구적으로 사용하자는 건의가 있었습니다.

"""

payload = {
    "content": summary,
    "username": "AI 업무 알리미"
}

requests.post(webhook_url, json=payload)
print("학교 업무 맞춤 요약 발송 완료")
