# 📋 homepage-school-board 스킬 이슈 트래커

> 스킬 버전: v0.1 | 생성: 2026-11-13

---

## 🟢 완료

_아직 없음 (v0.1 최초 생성)_

---

## 🔵 진행 중

### ISSUE-001: 학교 게시판 크롤러 + GitHub Actions 구축 (hc 학교)
- **상태**: 🔵 진행 중
- **대상 학교**: `school.gyo6.net/hc` (나이스 T0029 스킨)
- **목표 게시판**: 공지사항, 가정통신문
- **작업 목록**:
  - [x] 메인 HTML 탐색으로 `bbsId`·`mi` 파악
  - [ ] `scripts/crawl_notices.py` 완성 (bbsId 하드코딩 or 자동 감지)
  - [ ] `data/notices.json` 샘플 출력 확인
  - [ ] `.github/workflows/crawl_notices.yml` 작성
  - [ ] `school.html` 공지 탭 UI 추가
  - [ ] GitHub에 Push 후 Actions 첫 실행 확인
- **블로커**: 목록 URL의 Referer 체크 여부 확인 필요

---

## 📌 백로그

### ISSUE-002: 셀렉터 자동 감지 로직
- **우선순위**: Medium
- **설명**: probe 스크립트 실행 없이 `BOARD_CONFIGS`에 URL만 넣으면  
  셀렉터를 자동 추론하는 로직 추가
- **수락 기준**:
  - [ ] `table.board-list` / `ul.board-list` / `div.board-list` 순서로 fallback
  - [ ] 감지 실패 시 사용자에게 명확한 에러 메시지

### ISSUE-003: 여러 학교 지원 (멀티 사이트)
- **우선순위**: Low
- **설명**: `BOARD_CONFIGS`를 JSON/YAML 외부 파일로 분리해 학교별 설정 추가 편의 제고
- **수락 기준**:
  - [ ] `config/schools.yml` 파일에 학교별 URL·bbsId·이름 관리
  - [ ] 크롤러가 config 파일을 읽어 동적으로 처리

### ISSUE-004: 새 게시글 감지 알림 (선택)
- **우선순위**: Low
- **설명**: 새 글 등록 시 Supabase Edge Function 경유 FCM 푸시 발송  
  (업로드된 프로토타입 `school-notice-notifier` 활용)
- **참고**: 기존 프로토타입에 `GenericWebBoardCrawler` 이미 구현됨
- **수락 기준**:
  - [ ] 이전 notices.json과 diff 비교 → 신규 항목 추출
  - [ ] Supabase Functions 또는 GitHub Actions에서 FCM API 호출

### ISSUE-005: notices.json 보안 처리
- **우선순위**: Medium
- **설명**: 가정통신문에 학부모 연락처 등 개인정보 포함 가능성
- **수락 기준**:
  - [ ] 크롤러에서 전화번호·이메일 패턴 자동 마스킹 옵션
  - [ ] 또는 notices.json을 `.gitignore`에 추가하고 별도 Private 저장

### ISSUE-006: school.html 공지 탭 UX 개선
- **우선순위**: Low
- **설명**: 초기 버전 이후 UX 개선
- **수락 기준**:
  - [ ] 게시판별 뱃지(공지/가정통신) 색상 구분
  - [ ] 최신 글 "NEW" 뱃지 (3일 이내)
  - [ ] 무한 스크롤 또는 더보기 버튼

---

## 📝 변경 이력

| 날짜 | 버전 | 내용 |
|---|---|---|
| 2026-11-13 | v0.1 | 스킬 최초 생성, ISSUE-001~006 등록 |
