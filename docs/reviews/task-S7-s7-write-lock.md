# 검토: task/S7-s7-write-lock (PR #139)

- 검토: claude-web-yi2131@naver · 2026-11-27 (상시 일 S2)
- 참고: 이 검토를 올리기 전에 PR 이 이미 합쳐졌음(2026-11-28 확인). 아래 🟡 은 합쳐진 뒤에 남은 확인거리
- 대상: PR 머리 — main 기준. 설계 메모라 코드는 안 바뀜. 이 브랜치는 고치지 않았음
- **판정: 🟢 합쳐도 됨** (메모가 실제 코드와 맞음, 작은 보충 2개)

## 확인한 것

- 바뀐 파일은 `docs/plans/teacherlesson-schedule-write-lock.md` 와 작성자 일지뿐. 개인정보·비밀값 없음.
- 메모의 표를 지금 `skills/teacherlesson-schedule/server.py` 와 대조:
  - 쓰기 경로 줄 번호(`done` 461, `push` 493, `extend` 517, `pull` 554, `catch_up` 572, `move` 602, `swap` 621)와 개발 서버 `app.run(port=5000, debug=True)`(695) **모두 일치**.
  - `catch_up` 만 `_CATCH_UP_LOCK`(20줄)과 `ScheduleError` 처리(592줄)가 있고 나머지 6개는 `except ValueError` 만 있음 — 일치.
  - `done`(467줄)·`push`(498줄)의 `date.fromisoformat` 이 `try` 밖이라는 말도 맞음.
  - `_CATCH_UP_LOCK` 을 가리키는 시험이 **없음**(`grep` 결과 0건) → 메모가 권한 "별칭 한 줄"은 필요 없을 가능성이 큼.
  - 메모가 가리키는 시험 `tests/test_server_lessons_catchup.py`·`tests/test_server_write_routes_schedule_error.py` 가 실제로 있음(후자는 6곳을 임시로 고치면 "예상 밖 성공"으로 바뀌는 것을 앞서 PR #123 검토에서 확인).

## 🟡 보충

1. 메모의 데코레이터 예시는 `functools.wraps` 를 쓰는데, `server.py` 첫머리에 `import functools` 가 **없음**. 따라 하는 사람이 빠뜨리면 `NameError` — 한 줄 보충하면 좋음.
2. 데코레이터가 `ValueError` 를 `_action_error(str(exc))` 로 바꾸므로 `done`·`push` 의 날짜 오류가 500 HTML → 400 JSON 으로 **바뀜**(메모도 의도한 개선이라고 적음). 화면(`web`) 쪽이 오류 응답을 JSON 으로 읽는지 한 번 확인 필요(교사 PC).

## 확인 못 한 것

- 메모가 "줄 단위로 다 읽지 않았다"고 적은 `extend`·`pull`·`move`·`swap` 안쪽 오류 처리(실제 구현할 때 확인).
- 실제 시트로 두 탭에서 동시에 눌러 보기(T77, 교사 PC).
