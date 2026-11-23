# personal-vba-book 이슈 로그

> 이 스킬에서 생긴 문제와 해결 과정, 진행 중인 일, 할 일을 기록한다.
> 새 항목은 해당 절의 맨 위에 추가하고, 해결되면 '🟢 해결됨'으로 옮긴다.

## 🔵 진행 중

_없음_

## 📌 백로그

_없음_

## 🟢 해결됨

### ISSUE-002: Excel VBA 크롤러의 현대적 Python 마크다운 파이프라인 마이그레이션 (2026-10-24)
- **증상**: 기존 Excel VBA + Selenium Basic 기반 도서 크롤러가 브라우저 버전 충돌 및 엑셀 대용량 이미지 삽입 시 파일 깨짐 현상 발생
- **원인**: Selenium 및 브라우저 의존성, 엑셀 바이너리 파일(.xlsm)의 구조적 한계
- **해결/조치**:
  1. `migrate_bookshelf.py`로 엑셀 데이터 및 표지 165권을 Obsidian/Notion 호환 마크다운 카드로 일괄 추출
  2. `apply_card_template.py`로 초등 수업 연계 메타데이터(type, topics, subjects, pptx) 적용
  3. 전체 결과물을 `OneDrive - gyo6.net/8. 그림책과 서재`로 성공적 이관
- **관련 파일**: `migrate_bookshelf.py`, `apply_card_template.py`, `build_library.py`

### ISSUE-001: 국립중앙도서관 API 타임아웃 및 미조회 ISBN 예외 처리 (2026-10-24)
- **증상**: 도서 검색 시 국립중앙도서관 API 연결 지연 및 미등록 바코드 오류 발생
- **원인**: 공공 API 방화벽/응답 지연 및 바코드 스캔 오탈자
- **해결/조치**: YES24 직접 HTTP 경량 파싱으로 전환하고 예외 도서는 별도 스킵 로그 처리
- **관련 파일**: `migrate_bookshelf.py`
