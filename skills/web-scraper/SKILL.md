---
name: web-scraper
description: "URL을 주면 자동으로 웹 페이지를 수집(scraping)하고 로컬 검색 인덱스를 업데이트합니다. EduSearch(edusearch 레포)와 연동하여 여러 사이트 자료를 한 곳에서 검색할 수 있게 해줍니다."
---

# 웹 스크래퍼 + 로컬 검색 인덱서 스킬

URL을 제공하면 **자동으로 수집 → 인덱싱**하여 `http://localhost:5000`에서 검색 가능하게 만들어줍니다.

> **전제 조건**: `C:\Users\lee21\Documents\GitHub\edusearch\` 폴더에 EduSearch가 설치되어 있어야 합니다.
> 없다면 `git clone https://github.com/leechangsu2131/edusearch` 후 `pip install -r requirements.txt`

---

## 🤖 AI 에이전트 실행 순서

사용자가 "이 URL 수집해줘" 또는 "이 사이트 긁어줘"라고 하면:

1. **URL 확인** — 수집 대상 URL을 파악
2. **스크래핑 실행**
   ```powershell
   cd C:\Users\lee21\Documents\GitHub\edusearch
   python scraper.py --url <URL>
   ```
3. **인덱스 재생성**
   ```powershell
   python indexer.py
   ```
4. **결과 보고** — 수집된 제목, 키워드 요약 및 검색 방법 안내

---

## ⚙️ 옵션

| 상황 | 방법 |
|------|------|
| 일반 공개 페이지 | `python scraper.py --url <URL>` |
| 로그인 필요 페이지 | `python scraper.py --url <URL> --selenium` |
| 여러 URL 한 번에 | `python scripts/add_urls.py --urls "URL1" "URL2"` |
| 검색앱 실행 | `python search_app.py` → http://localhost:5000 |

---

## ⚠️ 주의사항

- **robots.txt 자동 체크** — 차단 여부 자동 확인
- **요청 간 5초 대기** — 서버 부하 방지
- **개인용 한정** — 수집 자료 외부 공유 금지
