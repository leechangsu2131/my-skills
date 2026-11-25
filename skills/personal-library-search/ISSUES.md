# personal-library-search 이슈 로그

> 이 스킬에서 생긴 문제와 해결 과정, 진행 중인 일, 할 일을 기록한다.
> 새 항목은 해당 절의 맨 위에 추가하고, 해결되면 '🟢 해결됨'으로 옮긴다. 양식은 맨 아래 주석 참고.

## 🔵 진행 중

_없음_

## 📌 백로그

### ISSUE-003: `parse_text_file` 가 '제목과 URL 이 한 줄'인 입력에서 제목을 잃음 (2026-11-25)
- **상태**: 📌 백로그
- **증상**: `책 제목 https://example.com/c` 한 줄이면 `raw_text` 가 빈 글로 나옴(앞 글 버림)
- **원인**: URL 이 있는 줄은 통째로 URL 로만 쓰고, 그 줄의 앞부분 글은 쓰지 않음
- **해결/조치**: 미정. 실제 books.txt 가 이런 모양인지는 확인 필요. 시험은 xfail
- **관련 파일**: `import_books.py` `parse_text_file`, `tests/test_pure_functions.py`

### ISSUE-002: `_title_score` 의 낱글자 비교 한계 (2026-11-25)
- **상태**: 📌 백로그
- **증상**: 글자만 같고 순서가 다른 제목(`abcabc` 와 `cbacba`)이 1.0(완전 일치)이 됨
- **원인**: 공통 글자 비율을 순서·개수 없이 셈
- **해결/조치**: 미정(서점 검색 결과 고르기에 영향이 있는지는 확인 필요). 시험은 xfail
- **관련 파일**: `add_and_sync_books.py` `_title_score`, `tests/test_pure_functions.py`

## 🟢 해결됨

### ISSUE-004: `library_notion_sync.py` 에 노션 DB ID 기본값이 코드에 박혀 있음 (2026-11-25)
- **상태**: 🟢 해결 (2026-11-25)
- **증상**: `os.getenv('NOTION_DATABASE_ID', '<32자리 ID>')` 처럼 기본값이 공개 저장소 소스와 `.env.example` 에 그대로 있었음. `load_env()` 도 부르지 않아 중앙 .env 를 읽지 못함
- **원인**: 초기 스크립트 형식이 남아 있었음
- **해결/조치**: 기본값을 코드·`.env.example` 에서 지우고(`.env.example` 은 자리표시 문구로), 다른 스크립트처럼 `load_env()` 로 중앙 .env 를 읽게 함. ID 와 토큰이 없으면 안내 후 멈춤. 시험(`tests/test_pure_functions.py`)이 32자리 ID 가 스킬 폴더의 .py·.env.example 에 다시 들어가지 않는지 확인. **이전 커밋 기록에는 값이 남아 있음**(공개 저장소 기록은 지우지 않음). 값 자체는 토큰 없이는 DB 에 접근할 수 없으나 안전을 위해 교사가 아직 쓰는 ID 인지 확인 필요. 이 기록에는 값을 쓰지 않음
- **교사 PC 확인 (2026-11-25, 검토)**: 지운 ID 는 지금도 쓰는 도서 DB 이고 중앙 .env 에 같은 값으로 들어 있음(키 이름만 확인). 공개 커밋 기록에는 남아 있지만 노션 토큰 없이는 열 수 없음
- **관련 파일**: `library_notion_sync.py`, `.env.example`, `tests/test_pure_functions.py`

### ISSUE-001: 노션 도서 DB 조회가 404 (2026-11-21)
- **상태**: 🟢 해결 (2026-11-21)
- **증상**: `databases/<ID>/query`가 `404 Not Found`. 공용 `NOTION_TOKEN`, `NOTION_API_KEY` 둘 다 같음.
- **원인**: 중앙 `.env`의 `PERSONAL_LIBRARY_SEARCH__NOTION_DATABASE_ID`가 지금 쓰는 「도서 신청 책 db」가 아닌 옛 ID였다. 공용 토큰도 이 DB에 연결되어 있지 않았다.
- **해결/조치**: 사용자가 준 토큰을 이 스킬 전용 키 `PERSONAL_LIBRARY_SEARCH__NOTION_TOKEN`으로 넣고(공용 `NOTION_TOKEN`은 다른 스킬이 써서 그대로 둠), 토큰의 `/v1/search` 결과에서 열 구성(제목·저자·도서관·ISBN·서점URL)이 맞는 DB ID로 고쳤다. 고치기 전 `.env`는 같은 폴더 `.env.bak_20261121`. DB가 또 404면 먼저 `/v1/search`(filter: database)로 토큰이 보는 DB 목록부터 확인한다.
- **관련 파일**: 중앙 `.env`

<!--
항목 양식 (복사해서 사용)

### ISSUE-001: 한 줄 제목 (YYYY-MM-DD)
- **상태**: 🔵 진행 중 | 📌 백로그 | 🟢 해결 (YYYY-MM-DD)
- **증상**: 무엇이 어떻게 안 됐나 (오류 메시지 그대로)
- **원인**: 확인된 원인
- **해결/조치**: 무엇을 바꿨나, 재발 방지
- **관련 파일**: `script.py`, 커밋 해시
-->
