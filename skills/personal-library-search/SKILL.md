---
name: 경주시립도서관 노션 연동 스크립트
description: 노션 도서 DB의 책 목록을 바탕으로 서점에서 ISBN/URL을 수집하고, 경주시립도서관 소장 여부를 확인하며, 미소장 도서는 희망도서 신청까지 자동화합니다
---

# 경주시립도서관 재고 및 노션 연동 자동화 봇

이 스킬은 **노션(Notion)의 도서 신청 데이터베이스**의 책 목록(제목, 저자)을 읽어와서:

1. 교보문고 검색을 통해 정확한 **ISBN-13**과 **서점 상품 페이지 URL**을 추출합니다.
2. 추출한 ISBN을 바탕으로 **경주시립도서관** 서버에 통합 검색을 수행합니다.
3. 소장된 도서는 소속 지점('시립', '송화', '단석', '칠평', '전자')을, 미소장 도서는 `미소장` 태그를 노션 DB에 업데이트합니다.
4. ISBN과 서점 URL도 노션에 함께 저장하여 나중에 올바른 책을 찾았는지 확인할 수 있습니다.
5. **(희망도서 신청)** 미소장 도서는 `request_books.py`로 경주시립도서관에 자동 신청할 수 있습니다.

## 필요 조건

- Python 3.8 이상
- `requests`, `beautifulsoup4` 라이브러리 설치
- `playwright` (희망도서 신청 시에만 필요)
- 노션 API 통합(Integration) 토큰
- 타겟 도서신청 DB의 노션 페이지 ID

## 사용 방법

### 1. 초기 설정

```bash
pip install -r requirements.txt
# 희망도서 신청 기능 사용 시
playwright install chromium
```

### 2. 환경 변수 세팅

`.env.example`을 `.env`로 복사 후 실제 값 입력:

```bash
cp .env.example .env
```

| 변수 | 설명 |
|------|------|
| `NOTION_TOKEN` | 노션 Integration 시크릿 토큰 |
| `NOTION_DATABASE_ID` | 도서신청 DB ID |
| `LIBRARY_ACCOUNT_N_ID` | 도서관 아이디 (신청용, 최대 10개) |
| `LIBRARY_ACCOUNT_N_PW` | 도서관 비밀번호 |

### 3. 노션 DB 구조

| 컬럼명 | 유형 | 설명 |
|--------|------|------|
| `제목` | Title | 책 제목 |
| `저자` | Rich Text | 저자명 |
| `도서관` | Multi-select | 소장처 태그 (시립/송화/단석/칠평/전자/미소장/신청완료) |
| `ISBN` | Rich Text | ISBN-13 (자동 입력) |
| `서점URL` | URL | 교보문고 상품 페이지 (확인용, 자동 입력) |

### 4. 도서관 소장 여부 검색 + 노션 업데이트

```bash
python add_and_sync_books.py
```

- 노션 DB의 모든 책에 대해 ISBN 검색 → 도서관 소장 확인 → 태그 업데이트
- 이미 ISBN이 입력된 책은 서점 재검색을 건너뜁니다
- 미소장 도서는 `미소장` 태그 + 실행 종료 시 요약 출력

### 5. 희망도서 신청 (미소장 도서)

```bash
# 먼저 테스트 (실제 신청 안 함)
python request_books.py --dry-run

# 실제 신청 (최대 2권)
python request_books.py --max-books 2

# 모든 미소장 도서 신청 (계정 로테이션)
python request_books.py
```

- 노션에서 `미소장` 태그가 달린 책을 자동으로 찾아 신청합니다
- 1인 월 2권 제한 → 한도 도달 시 자동으로 다음 계정으로 전환
- 신청 성공 시 노션 태그가 `신청완료`로 업데이트됩니다

## 주의 사항

- 검색 정확도를 극대화하기 위해 '제목'과 '저자' 컬럼의 데이터가 정확하게 입력되어 있으면 좋습니다
- `서점URL`을 통해 잘못된 책을 검색한 것이 아닌지 확인할 수 있습니다
- 희망도서 신청 시 `--dry-run`으로 먼저 테스트를 권장합니다
- `library_notion_sync.py`, `resync_14books.py`는 이전 특수 작업용 스크립트입니다
