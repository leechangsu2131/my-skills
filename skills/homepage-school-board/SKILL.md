---
name: homepage-school-board
description: >-
  학교 홈페이지 게시판(공지사항·가정통신문 등)을 크롤링하여 GitHub Actions로
  매일 1회 자동 수집하고, 결과를 data/notices.json에 커밋한 뒤
  school.html의 공지사항 탭에서 정적으로 표시하는 전체 파이프라인을 구축한다.
  나이스(gyo6.net) 계열 학교 홈페이지 표준 패턴을 지원하며,
  CSS 셀렉터·bbsId 설정만 바꾸면 타 학교에도 재사용 가능하다.
  사용자가 "학교 게시판 연동", "공지사항 크롤링", "GitHub Actions 스케줄 크롤러" 등을 요청할 때 활성화한다.
---

# 🏫 학교 게시판 → 홈페이지 자동 연동 스킬

학교 홈페이지 게시판을 **GitHub Actions(매일 1회)** 로 크롤링 →  
`data/notices.json` 커밋 → `school.html` 공지탭 표시까지 한 번에 구축한다.

> **전제 조건**: `leechangsu2131.github.io` (또는 동일 구조의) GitHub Pages 저장소

---

## 📐 아키텍처

```
학교 홈페이지 게시판
       ↓ Python + httpx/BeautifulSoup
GitHub Actions (cron: 매일 KST 07:00)
       ↓ 변경 시 자동 git commit & push
data/notices.json  (최신 50건 × 게시판 수)
       ↓ fetch()
school.html — 📢 공지 탭
```

**서버·DB 없음** — 완전 정적, 무료.

---

## 📁 생성 파일 목록

| 경로 | 역할 |
|---|---|
| `scripts/crawl_notices.py` | 크롤러 본체 |
| `data/notices.json` | 크롤링 결과 (자동 갱신) |
| `.github/workflows/crawl_notices.yml` | 스케줄 워크플로우 |
| `school.html` | 공지 탭 UI 추가 |

---

## 🤖 에이전트 실행 순서

### STEP 1 — 학교 홈페이지 URL 패턴 파악

1. 메인 페이지 HTML 다운로드 후 `bbsId`, `nttSn`, `selectNttList.do` 패턴 추출
2. 나이스 표준 패턴 감지:
   - 목록: `https://<도메인>/hc/na/ntt/selectNttList.do?mi=<mi>&bbsId=<bbsId>`
   - 상세: `https://<도메인>/hc/na/ntt/selectNttInfo.do?mi=<mi>&nttSn=<nttSn>`
3. 공지사항/가정통신문 `mi` + `bbsId` 조합 확인
4. 셀렉터 검증: 목록 HTML에서 `ul.se-ul li` 또는 `table.board-list tbody tr` 패턴 확인

참고 스크립트: [scripts/probe_school.py](./scripts/probe_school.py)

### STEP 2 — 크롤러 스크립트 생성

[scripts/crawl_notices.py](./scripts/crawl_notices.py) 생성:
- `BOARD_CONFIGS` 상수에 게시판별 `mi`, `bbsId`, `name` 설정
- 나이스 표준 목록 API 또는 HTML 파싱 선택
- 결과를 `data/notices.json`으로 저장 (최신 50건)
- 실행: `python scripts/crawl_notices.py`

### STEP 3 — GitHub Actions 워크플로우 생성

`.github/workflows/crawl_notices.yml` 생성:
```yaml
schedule:
  - cron: '0 22 * * *'   # KST 07:00 = UTC 22:00 (전날)
```
- `workflow_dispatch` 트리거로 수동 실행도 지원
- `notices.json` 변경 시에만 커밋 (변경 없으면 no-op)

### STEP 4 — school.html 공지 탭 추가

기존 탭(시간표·급식·학사일정·학교정보)에 **📢 공지** 탭 추가:
- `fetch('data/notices.json')` 로드
- 게시판별 섹션 카드로 렌더링
- 클릭 → 학교 원문 링크 새 탭 열기
- 로딩 스피너 + 에러 fallback 처리

### STEP 5 — 테스트 & 첫 커밋

```powershell
# 로컬 테스트
cd C:\Users\lee21\Documents\GitHub\HomePage
python scripts/crawl_notices.py

# 결과 확인
cat data/notices.json

# 커밋
git add data/notices.json scripts/crawl_notices.py .github/workflows/crawl_notices.yml school.html
git commit -m "feat: 학교 게시판 크롤링 자동화"
git push
```

---

## ⚙️ 설정 옵션

| 항목 | 기본값 | 변경 위치 |
|---|---|---|
| 크롤링 시각 | KST 07:00 | `.github/workflows/crawl_notices.yml` cron |
| 최대 보관 건수 | 50건/게시판 | `crawl_notices.py` `MAX_POSTS` |
| 게시판 목록 | 공지사항·가정통신문 | `crawl_notices.py` `BOARD_CONFIGS` |
| 셀렉터 | 나이스 표준 | `crawl_notices.py` `SELECTORS` |

---

## 📌 나이스 gyo6.net 패턴 레퍼런스

참고: [references/neis_gyo6_pattern.md](./references/neis_gyo6_pattern.md)

---

## ⚠️ 주의사항

- `robots.txt` 및 학교 홈페이지 이용약관 확인 후 사용
- GitHub Actions 1회 실행 시 ~1분 소요 (월 무료 2,000분 내 충분)
- 학교 사이트가 IP 차단 시 `User-Agent` 조정 또는 크롤링 중단
- 개인정보(학부모 연락처 등)가 게시판에 있을 경우 `notices.json` 비공개 처리 필요
