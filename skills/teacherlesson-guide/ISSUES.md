# teacherlesson-guide 이슈 로그

> 이 스킬에서 생긴 문제와 해결 과정, 진행 중인 일, 할 일을 기록한다.
> 새 항목은 해당 절의 맨 위에 추가하고, 해결되면 '🟢 해결됨'으로 옮긴다.
> 2026-11-22 guide-splitter·guide-mapper·수업 비서의 지도서 받기를 이 스킬로 합쳤다. 그 전 기록은 teacherlesson-assistant ISSUES 의 '요청됨 (2026-11-20)' 절.

## 🔵 진행 중

### ISSUE-002: 저장소 기록에 출판사 지도서 분할 PDF 가 남아 있음 (2026-11-22)
- **상태**: 🔵 진행 중 (사람 결정 필요)
- **증상**: 옛 splitter 의 `tmp_output_save/art/pdf_splits/*.pdf`(미술 지도서 분할본 15개, 약 72MB)와 `tmp_*` 시험 결과가 2026-04-14 부터 공개 저장소에 커밋돼 있었음
- **조치**: 2026-11-22 추적 해제(`git rm --cached`, 파일은 PC 에 남김) + `.gitignore`
- **남은 일**: 지난 커밋 기록에서도 지우려면 기록 다시 쓰기(filter-repo)와 강제 푸시가 필요 → 저장소 주인 결정

## 📌 백로그

### ISSUE-003: 지도서 처리 남은 일 (수업 비서에서 옮김, 2026-11-22)
- guide-mapper 대체 매칭: 3-1 국어를 다시 만들면 독서·매체 행이 3-2 PDF를 가리킴(이 PC에 3-1 PDF 없음). 학년·학기가 다르면 대체 매칭에서 빼기
- `split_by_lesson_headers` 재실행 시 예전 `pdf_splits` 조각이 남음 / `apply_annual_plan` 의 `groups.orig.json` 이 첫 분할 것만 보관
- 아이스크림 자동 로그인 불안정: 크롬 저장 비밀번호가 사람 클릭 전에는 칸에 안 채워질 때가 있음 (지도서 파일 자체는 로그인 없이 받아짐)
- 음악 지도서 분할본(`D:\지도서\음악\pdf_splits`)이 이 PC에 없음 — 진도표 경로는 그곳을 가리킴
- mapper 의 `.env` 대체 경로가 옛 `teacher-schedule\.env` 를 가리킴 → 중앙 .env 만 쓰도록 정리

### ISSUE-001: 새 지도서는 노트북(Gemini) 먼저 시험 (2026-11-22)
- 새 출판사·새 학년 지도서에서 `util-notebooklm` `find` 로 차시별 쪽 표를 받아 groups.json 을 만드는 작은 변환기 만들기. splitter 규칙 수정보다 먼저 시도

## 🟢 해결됨

_없음_
