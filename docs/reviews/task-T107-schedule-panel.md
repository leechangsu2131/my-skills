# 검토: task/T107-schedule-panel (PR #183 — 📅 오늘·이번 주 일정과 할 일 칸)

- 검토: claude · 2026-11-28 (상시 일 S2)
- 대상 커밋: `28808cd` — main 기준 충돌 없음(단독)
- **판정: 🟢 합치기 권함** (🟡 두 가지는 알아 두기)

## 확인한 것

- 이 브랜치에서 `tests/test_schedule_panel.py` 31개·`node tests/test_agenda.js` 8개 통과, 서버 시험 통과, 그 폴더 `pytest tests` 504 통과·기존 xfail 4.
- 읽기 중심: 시트에 쓰는 것은 '빠른 할 일' 한 줄뿐이고 서버는 `confirm: true` 일 때만 씀. 화면은 `window.confirm` 창을 한 번 거쳐야 보냄. 쓸 때 `RAW` 로 넣어 `=` 로 시작하는 글이 수식이 되지 않게 함.
- 오류 문구가 시트 주소·계정 주소를 새지 않게 줄여 보여 줌(`explain` — 알 수 없는 오류는 종류만, `SystemExit`·`ValueError` 는 첫 줄만). 시트 읽기 결과는 10분(실패는 1분) 캐시, 잠금 사용.
- 학교 일정 글은 모두 `agendaEsc` 로 막은 뒤 `innerHTML` 에 넣음. 위쪽 한 줄은 **개수만** 보여 줘 수업 화면을 학생이 봐도 내용이 안 보임. 🎯 수업 진행 화면에서는 숨김.
- `school-todo-kakao`·`gspread` 는 쓸 때만 불러와서 없으면 칸만 안내 문구를 띄우고 수업 비서는 그대로 켜짐.

## 🟡 알아 둘 것

- **다른 스킬의 비공개 속성을 씀**: 쓰기에서 `inbox._ws.append_row(...)` 를 직접 부름(`schedule_panel.py` `Panel.quick`). `school-todo-kakao` 가 `_ws` 이름을 바꾸면 조용히 깨짐. `schooltodo/inbox.py` 에 '한 줄 덧붙이기' 공개 함수를 두고 그것을 부르는 편이 안전함(그 스킬은 묶음 밖이라 이 PR 에서 고치지 말고 ISSUES 에 한 줄 권함).
- **서비스 계정 설정이 서버 프로세스 환경 변수로 들어감**: `apply_settings` 가 `GOOGLE_SERVICE_ACCOUNT_JSON` 등을 `os.environ` 에 올림. 이후 서버가 띄우는 프로그램(ffmpeg·Chrome 등)이 그 값을 물려받음. 읽기 전용 시트라 위험은 낮지만, 가능하면 시트를 여는 순간에만 쓰고 지우거나 `SheetsDb` 에 값을 직접 넘기는 쪽이 낫다(확인 필요: `SheetsDb.from_env()` 가 환경 변수만 읽는지).

## 못 한 것

- 실제 Google 시트 읽기·'빠른입력' 쓰기는 시험하지 못함(가짜 시트만). PR·ISSUES 에도 교사 PC 확인으로 적혀 있음.

## 다른 PR 과 함께 합칠 때

- #179(T106)·#181(T109)와 `assistant_server.py` 에서 줄이 겹쳐 충돌함(아래 '합치는 순서').
