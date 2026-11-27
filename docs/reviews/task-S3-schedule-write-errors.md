# 검토: task/S3-schedule-write-errors (PR #123)

- 검토: claude-web-yi2131@naver · 2026-11-27 (상시 일 S2)
- 대상 커밋: `pr123` 머리 — main 기준. 이 브랜치는 고치지 않았음
- **판정: 🟢 합치기 권함 — 단, 같은 일을 한 PR #124 와 하나만**

## 확인한 것

- `skills/teacherlesson-schedule` 에서 `python -m unittest tests.test_server_write_errors` → 3개 중 통과 1(ValueError 는 400 JSON), 예상된 실패 2. (flask·flask-cors 필요 — `requirements.txt` 에 있음)
- 현재 `server.py` 에서 `done`·`push`·`extend`·`pull`·`move`·`swap` 은 `except ValueError` 만 있음을 직접 확인(`catch-up` 만 `ScheduleError` 를 따로 받음).
- 6곳에 `except schedule.ScheduleError → _action_error(…, 500)` 를 임시로 더해 보니 두 시험이 **"unexpected success"** 로 바뀜 → 고치는 사람에게 알려 주는 장치가 동작함. 확인 뒤 `server.py` 는 되돌림.
- 6개 경로 전부를 `subTest` 로 돌려 한 경로만 고쳐도 남은 경로가 드러남. ISSUES.md ISSUE-005 에 시험 위치를 적음. 개인정보·비밀값 없음.

## 🟡 겹침

- **PR #124(`task/S3-s3-write-paths`)가 같은 ISSUE-005 에 같은 6개 경로 시험을 따로 올림**(`tests/test_server_write_routes_schedule_error.py`). 둘 다 합치면 시험이 두 벌이고 `ISSUES.md` 같은 줄이 충돌함. 하나만 합치고 다른 하나는 닫기를 권함.
  - #123 은 연결 단계·읽기 단계를 나눠 두 시험 + 400 대조 시험. #124 는 오류 종류 2가지를 도는 방식(내용은 읽기만 함, 돌려 보지는 않음 — **확인 필요**).
- 시험 머리말에 "xfail(strict)"라고 적었지만 실제는 `unittest.expectedFailure`. 말만 고치면 됨.

## 확인 못 한 것

- 진짜 시트·서버 실행(교사 PC). T77(쓰기 잠금)이 같은 함수를 고치므로 그 PR 과 겹칠 수 있음.
