# teacherlesson-schedule 이슈 로그

> 이 스킬에서 생긴 문제와 해결 과정, 진행 중인 일, 할 일을 기록한다.
> 새 항목은 해당 절의 맨 위에 추가하고, 해결되면 '🟢 해결됨'으로 옮긴다. 양식은 맨 아래 주석 참고.

## 🔵 진행 중

_없음_

## 📌 백로그

### ISSUE-003: `test_auto_planner` 시험 1개가 원래부터 실패함 (2026-11-25)
- **상태**: 📌 백로그
- **증상**: `pytest tests/test_auto_planner.py` 에서 `test_resolve_progress_worksheet_skips_invalid_first_candidate` 가 `ValueError: Could not find a progress sheet. Checked: ?쒗듃1` 로 실패. 내 변경을 모두 빼고(`git stash -u`) 돌려도 똑같이 실패(나머지 9개는 통과)
- **원인**: 확인 필요. 추정 — 시험 안의 한글 시트 이름(예: "시트1")이 글자 깨짐(인코딩)으로 `?쒗듃1` 처럼 바뀌어 후보 이름이 서로 안 맞는 것으로 보임
- **해결/조치**: 아직 안 함(T04 범위 밖). 시험 파일 인코딩과 `auto_planner.py` 의 후보 이름 비교를 확인할 것
- **관련 파일**: `tests/test_auto_planner.py`, `auto_planner.py`

### ISSUE-002: `/api/lessons` 가 '날짜 시각' 모양의 slot_date 에서 죽음 (2026-11-25)
- **상태**: 📌 백로그
- **증상**: 수업배치 시트의 `slot_date` 가 `2026-12-01 00:00:00` 처럼 시각이 붙어 있으면 `ValueError: 계획일 날짜 형식이 올바르지 않습니다` 가 `try` 밖에서 올라와 JSON 이 아닌 500 응답이 됨
- **원인**: `server.py` 는 `slot_date` 를 `[:10]` 으로 잘라 쓰려고 하지만, 그 앞의 정렬(`schedule._bridge_row_sort_key` → `_parse_date`)이 `YYYY-MM-DD` 만 받음. 실제 시트에 시각이 붙는지는 확인 필요(추정: 붙으면 문제)
- **해결/조치**: 아직 안 함. 재현 시험 `test_bridge_date_with_time_suffix_is_cut_to_ten_chars` 를 xfail 로 둠(고쳐지면 xfail 표시를 지울 것). 고치는 방향 후보 — 정렬 전에 날짜를 먼저 잘라 주기, 또는 정렬 오류도 JSON 오류로 돌려주기
- **관련 파일**: `server.py`(`subject_lessons`), `schedule.py`(`_bridge_row_sort_key`, `_parse_date`), `tests/test_server_lessons_catchup.py`

### ISSUE-001: `/api/catch-up` 가 시트 읽기 실패(ScheduleError)를 JSON 오류로 안 바꿈 (2026-11-25)
- **상태**: 📌 백로그
- **증상**: `schedule.connect()`·`load_all()` 이 `ScheduleError`(`SheetFormatError`·`ConfigurationError` 등)를 내면 `/api/catch-up` 은 처리하지 못하고 오류가 그대로 올라옴(서버 500). 같은 서버의 `/api/lessons` 는 `(ValueError, ScheduleError)` 둘 다 잡아 JSON 오류를 돌려줌
- **원인**: `catch_up`(그리고 `done`·`push`·`extend`·`pull`·`move`·`swap` 도 `except ValueError` 만 있음 — 시험으로는 `catch_up` 만 확인)이 `except ValueError` 만 씀. `ScheduleError` 는 `ValueError` 의 하위 클래스가 아님. 화면이 JSON 오류를 기대하는지는 확인 필요
- **해결/조치**: 아직 안 함. 재현 시험 `test_schedule_error_returns_json_error_like_lessons_endpoint` 를 xfail 로 둠. 고치는 방향 후보 — `except (ValueError, schedule.ScheduleError)`
- **관련 파일**: `server.py`(`catch_up` 외), `tests/test_server_lessons_catchup.py`


## 🟢 해결됨

### ISSUE-004: /api/catch-up 동시 요청이 수업배치 갱신을 덮지 않도록 잠금 (2026-11-25)
- **상태**: 🟢 해결 (2026-11-25)
- **증상**: 동시에 들어온 두 요청이 같은 시트 내용을 읽고 각각 전체 수업배치를 다시 쓰면, 나중 저장이 먼저 저장한 변경을 덮을 수 있음
- **원인**: 읽기와 변경 작업을 묶어 보호하는 잠금이 없음
- **해결/조치**: `/api/catch-up` 의 시트 연결·읽기·변경 구간을 `threading.Lock` 으로 보호. 두 번째 요청은 첫 번째 작업이 끝난 뒤 최신 내용을 읽음. 두 요청을 동시에 보내도 작업 구간이 겹치지 않는 가짜 시험 추가
- **관련 파일**: `server.py`, `tests/test_server_lessons_catchup.py`

<!--
항목 양식 (복사해서 사용)

### ISSUE-001: 한 줄 제목 (YYYY-MM-DD)
- **상태**: 🔵 진행 중 | 📌 백로그 | 🟢 해결 (YYYY-MM-DD)
- **증상**: 무엇이 어떻게 안 됐나 (오류 메시지 그대로)
- **원인**: 확인된 원인
- **해결/조치**: 무엇을 바꿨나, 재발 방지
- **관련 파일**: `script.py`, 커밋 해시
-->
