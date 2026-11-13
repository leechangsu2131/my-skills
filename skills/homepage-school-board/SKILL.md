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
`data/notices.json` 자동 커밋 → `school.html` 공지 탭(실시간 검색·필터·새로고침) 표시까지 한 번에 구축한다.

> **전제 조건**: `leechangsu2131.github.io` (또는 동일 구조의) GitHub Pages 정적 웹사이트

---

## 📐 아키텍처

```
학교 홈페이지 게시판 (나이스 T0029 등)
       ↓ Python (urllib + re / 추가 패키지 없이 경량 동작)
GitHub Actions (cron: 매일 KST 07:00 / workflow_dispatch 수동 실행)
       ↓ 변경 시 자동 git commit & push
data/notices.json  (최신 공지사항 + 가정통신문 피드)
       ↓ fetch() 비동기 로드
school.html — 📢 공지 탭 (실시간 검색 · 칩 필터 · NEW 뱃지 · 새로고침)
```

**서버·DB 없음** — 완전 정적, 무과금 자동화.

---

## 📁 파일 구성

| 경로 | 역할 |
|---|---|
| `scripts/crawl_notices.py` | 크롤러 본체 (EUC-KR/UTF-8 자동 판별, 표준 파서) |
| `data/notices.json` | 크롤링 결과 JSON (GitHub Actions에 의해 매일 갱신) |
| `.github/workflows/crawl_notices.yml` | GitHub Actions 스케줄 워크플로우 (KST 07:00 실행) |
| `school.html` | 공지 탭 UI (실시간 검색창, 카운트 뱃지, 새로고침, 원문 링크) |

---

## 🤖 에이전트 실행 순서

### STEP 1 — 학교 홈페이지 URL 패턴 파악

1. 학교 메인 페이지 HTML 다운로드 후 `bbsId`, `nttSn`, `selectNttList.do` 패턴 추출
2. 나이스 표준 패턴 감지:
   - 목록: `https://<도메인>/hc/na/ntt/selectNttList.do?mi=<mi>&bbsId=<bbsId>`
   - 상세: `https://<도메인>/hc/na/ntt/selectNttInfo.do?mi=<mi>&bbsId=<bbsId>&nttSn=<nttSn>`
3. 공지사항/가정통신문 `mi` + `bbsId` 조합 확인
4. 셀렉터 검증: 목록 테이블의 `<td class="bbs_tit">` 안 `<a data-id="nttSn" class="nttInfoBtn">`

참고 도구: [scripts/probe_school.py](./scripts/probe_school.py)

### STEP 2 — 크롤러 스크립트 작성 (`scripts/crawl_notices.py`)

- `BOARD_CONFIGS` 상수에 게시판별 `mi`, `bbs_id`, `board_name` 지정
- 외부 의존성(pip) 없이 파이썬 내장 `urllib`과 정규표현식(`re`)으로 고속 크롤링
- UTF-8 및 EUC-KR 인코딩 자동 폴백 지원
- 결과: `data/notices.json` 저장

### STEP 3 — GitHub Actions 워크플로우 작성

`.github/workflows/crawl_notices.yml`:
```yaml
name: Crawl School Notices
on:
  schedule:
    - cron: '0 22 * * *'   # KST 07:00 (UTC 22:00 전날)
  workflow_dispatch:        # 수동 즉시 실행 지원

jobs:
  crawl:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python scripts/crawl_notices.py
      - run: |
          git config --local user.email "github-actions[bot]@users.noreply.github.com"
          git config --local user.name "github-actions[bot]"
          git add data/notices.json
          git diff --staged --quiet || (git commit -m "chore(data): 학교 공지사항 자동 갱신 [skip ci]" && git push)
```

### STEP 4 — school.html 탭 & 고도화 UI 연동

- **실시간 검색창**: 검색어 입력 시 제목/작성자 실시간 필터링 + ✕ 지우기 버튼
- **필터 칩**: [전체 (N)], [공지사항 (N)], [가정통신문 (N)] 게시글 수 동적 집계
- **시각적 강조**: 4일 이내 등록 글 `NEW` 뱃지, `통합공지` 뱃지
- **원문 연결**: 클릭 시 학교 홈페이지 원문 상세 페이지 새 탭 오픈
- **수동 재조회**: 캐시 무효화 쿼리스트링(`?v=Date.now()`) 기반 `🔄 새로고침` 버튼

---

## ⚙️ 설정 옵션

| 항목 | 기본값 | 변경 위치 |
|---|---|---|
| 크롤링 주기 | 매일 KST 07:00 | `.github/workflows/crawl_notices.yml` cron |
| 최대 수집 건수 | 게시판당 30건 | `scripts/crawl_notices.py` `MAX_POSTS` |
| 대상 학교/게시판 | 화천초 (공지/가통) | `scripts/crawl_notices.py` `BOARD_CONFIGS` |

---

## 📌 나이스 gyo6.net 패턴 레퍼런스

참고: [references/neis_gyo6_pattern.md](./references/neis_gyo6_pattern.md)
이슈 추적: [ISSUES.md](./ISSUES.md)
