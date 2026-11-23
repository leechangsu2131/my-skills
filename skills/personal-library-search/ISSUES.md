# personal-library-search 이슈 로그

> 이 스킬에서 생긴 문제와 해결 과정, 진행 중인 일, 할 일을 기록한다.
> 새 항목은 해당 절의 맨 위에 추가하고, 해결되면 '🟢 해결됨'으로 옮긴다. 양식은 맨 아래 주석 참고.

## 🔵 진행 중

_없음_

## 📌 백로그

_없음_

## 🟢 해결됨

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
