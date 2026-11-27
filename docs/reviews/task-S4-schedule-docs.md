# 검토: task/S4-schedule-docs (PR #142)

- 검토: claude-web-은정 · 2026-11-27 (상시 일 S2)
- 대상 커밋: `82da69e` — main `0e7e1da` 에 합쳐 본 상태(충돌 없음)
- **판정: 🟢 합치기를 권함** (아래 🟡 한 줄은 합친 뒤 고쳐도 됨)

## 확인한 것

- `tests/` 의 시험 파일 8개가 SKILL.md 목록·README·두 확인 명령과 일치.
- `python schedule.py tomorrow`·`thisweek` 명령이 코드에 있음(코드 읽기, 실행 안 함).
- `SHEET_NAME` 기본값 `시트1` 이 `auto_planner.py` 에 있고, ISSUE-003·6 이 '해결됨'에 있음.
- README 의 새 상대 경로 `docs/bridge-sheet-design.md` 파일이 있음. 개인 PC 절대 경로가 빠짐.
- PR 자동 검사의 teacherlesson-schedule 칸: 138 통과 · 6 xfail(합 144, PR 설명의 144개와 맞음).
- `tools/check_privacy.py --stdin` 경고 0. 바뀐 파일은 문서 2개와 작업자 일지.

## 🟡 남은 낡은 문장

- SKILL.md 확인 절의 "없으면 **서버 시험 2개 파일**이 시작도 못 합니다": 지금은 파일 맨 위에서 `server`(→ `fitz`)를 불러오는 시험이 **3개**(`test_server`·`test_server_lessons_catchup`·`test_server_write_routes_schedule_error`)이고, `test_korean_restore` 의 시험 일부도 안에서 `server` 를 불러옴(코드 읽기, `fitz` 없이 돌려 보지는 못함).

## 확인 못 한 것

- 이 환경에는 `flask_cors`·PyMuPDF 가 없어 확인 명령을 그대로 돌리지 못함. `npm.cmd run build`.
