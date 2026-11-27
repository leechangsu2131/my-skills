# teacherlesson-schedule 이슈 로그

> 이 스킬에서 생긴 문제와 해결 과정, 진행 중인 일, 할 일을 기록한다.
> 새 항목은 해당 절의 맨 위에 추가하고, 해결되면 '🟢 해결됨'으로 옮긴다. 양식은 맨 아래 주석 참고.

## 🔵 진행 중

_없음_

## 📌 백로그

### ISSUE-7: `requirements.txt` 에 PyMuPDF 가 없음 (2026-11-26)
- **상태**: 🟢 해결(T93, 2026-11-27)
- **증상**: `server.py` 는 첫머리에서 `import fitz`(PyMuPDF)를 하는데 `requirements.txt` 에 없음. `fitz` 가 없는 곳에서 서버 시험 2개 파일이 `ModuleNotFoundError: No module named 'fitz'` 로 시작도 못 함 → 새 PC 에서 `pip install -r requirements.txt` 만 하면 서버가 안 켜질 것(추정)
- **원인**: 목록 빠뜨림
- **해결/조치**: `requirements.txt` 에 `PyMuPDF>=1.24` 추가(teacherlesson-assistant 와 같은 표기). 요구 파일만으로 만든 새 가상환경에서 시험 91개 중 90개 통과, 서버 시험 2개 파일이 이제 시작됨. 실패 1개는 ISSUE-003 의 원래부터 실패하던 시험. CI(check.yml)의 schedule 칸 `extra: PyMuPDF` 는 이제 필요 없음(공용 파일이라 PR 설명으로 제안)
- **관련 파일**: `requirements.txt`, `server.py`

## 🟢 해결됨

### ISSUE-005: `/api/catch-up` 밖의 쓰기 경로 6개도 ScheduleError 를 JSON 오류로 안 바꿈 (2026-11-26, 2026-11-27 해결)
- **상태**: 🟢 해결됨 (T100). 잠금(ISSUE-004 한계)은 아직 — T77
- **증상**: `/api/done`·`push`·`extend`·`pull`·`move`·`swap` 은 `except ValueError` 만 있어, 시트 읽기·머리글 문제(`ScheduleError`)가 나면 JSON 이 아닌 서버 오류 화면이 됐다(수업 비서에는 "알 수 없는 오류").
- **해결**: `server.py` 에 `_json_schedule_errors` 데코레이터(`ScheduleError` → `{"status":"error","message":…}` + 500)를 만들어 6개 경로의 `@app.route` 바로 아래에 붙임. 경로 안의 `ValueError`→400 처리는 그대로. 잠금은 하지 않음(T77, 설계는 `docs/plans/teacherlesson-schedule-write-lock.md`)
- **시험**: `tests/test_server_write_routes_schedule_error.py` — expectedFailure 6개를 일반 시험으로(고치기 전엔 모두 실패). 변이 3가지(잡는 예외 바꾸기·상태 400·`swap` 에서 데코레이터 빼기) 모두 잡힘. 수업 비서 쪽은 `teacherlesson-assistant/tests/test_progress_legacy_errors.py` 6개 — 옛 진도 서버의 JSON 오류 문장을 그대로 넘기고, JSON 이 아니면 "진도 서버 오류 500", 꺼졌으면 "꺼져 있어요" (`assistant_server.py` 는 고칠 필요 없었음. 화면은 `j.message` 를 토스트로 보임)
- **남은 것**: `pull`·`move`·`swap` 은 수업 비서가 `PROGRESS_ACTIONS` 로 넘기지 않아 이 서버 화면에서 직접 쓸 때만 해당. 실제 시트 확인은 교사 PC
- **관련 파일**: `server.py`(`_json_schedule_errors`), `tests/test_server_write_routes_schedule_error.py`, `../teacherlesson-assistant/tests/test_progress_legacy_errors.py`

### ISSUE-6: `auto_planner.py`·`schedule.py`·`server.py` 에 깨진 한글이 코드에 그대로 들어 있음 (2026-11-26, 2026-11-27 해결)
- **상태**: 🟢 해결됨 (T92)
- **증상**: 안내·오류 문구가 `珥덇린 …` 처럼 읽을 수 없게 나왔고, 동작에 쓰는 이름도 깨져 있었다 — 기본 진도표 시트 이름(`?쒗듃1`), 휴업일 날짜 칸 이름(못 찾으면 첫 칸을 읽음), 진도표의 `과목`·`차시` 칸 이름(`auto_planner`), 진도 출력의 `전체`·`완료`·`진도율` 키(항상 0 으로 나옴), `server.py` 의 `계획교시` 이름
- **원인**: UTF-8 한글이 다른 인코딩으로 잘못 읽힌 채 저장됨(추정). 한글 3바이트 중 앞 2바이트가 `?` 한 글자로 바뀐 곳이 있어 글자를 기계로 되살릴 수 없었음
- **해결**: 세 파일의 깨진 글자 약 90줄을 문맥(코드 이름·메시지 뜻)으로 읽어 되살림. 코드(식별자)는 그대로 두고 글자만 바꿈. 알 수 없던 장식 기호(이모지 등)는 `[설정]` 같은 글자로 대신함
- **시험**: `tests/test_korean_restore.py` 17개 — 기본 시트 이름(환경값 없이)·휴업일 날짜 칸이 둘째 칸일 때·첫 칸·헤더 없을 때·빈/읽을 수 없는 날짜·없는 시트·기초시간표 요일·진도율 출력(50.0%, 2/4)·계획교시 대체 이름·소스 안에 한자/대체 문자/'?'+한글이 없는지 검사. 되살리기 전 14개 실패 → 후 모두 통과. 소스를 틀리게 한 변이 5개 중 4개를 시험이 잡음(`.replace("요일", "")` 은 결과가 같아 못 잡음 — 동작에 영향 없음)
- **남은 것**: 실제 시트에서 휴업일 날짜 칸이 몇 번째인지, 이모지 자리에 뭐가 있었는지는 확인 필요(교사 PC). `auto_planner.py` 에는 `resolve_progress_worksheet` 가 두 번 정의돼(133·528줄) 앞의 한국어 오류 문구 쪽은 쓰이지 않음(뒤의 영어 문구가 쓰임) — 정리는 아직 안 함
- **관련 파일**: `auto_planner.py`, `schedule.py`, `server.py`, `tests/test_korean_restore.py`

### ISSUE-003: `test_auto_planner` 시험 1개가 원래부터 실패함 (2026-11-25, 2026-11-27 해결)
- **상태**: 🟢 해결됨 (T92)
- **증상**: `test_resolve_progress_worksheet_skips_invalid_first_candidate` 가 `Checked: ?쒗듃1` 로 실패
- **원인**: `auto_planner.py` 기본 시트 이름이 깨져 있었음(ISSUE-6)
- **해결**: 기본값을 "시트1" 로 되살림. 환경값 없이 `tests.test_auto_planner` 통과 확인
- **관련 파일**: `auto_planner.py`, `tests/test_auto_planner.py`

### ISSUE-8: `semester_rollover.py` 의 완료 기준(규칙)에 `unit`·`title` 이 하나도 없으면 모든 행이 완료로 칠해짐 (2026-11-27)
- **상태**: 🟢 해결 (2026-11-27)
- **증상**: `matches(row, rule)` 은 규칙의 `unit`·`title` 만 보고, 없으면 빈 글자로 비교해 **모든 행에 맞는다**. 설정 JSON 의 `done_until_new`·`done_until_existing` 규칙에서 `title` 을 `tilte` 처럼 오타 내거나 빠뜨리면 `mark_until` 이 그 과목 **전 행을 완료로 칠하고**, "다음 수업: 없음(모두 완료)"로 나옴. 확인: `mark_until(rows, {"tilte": "a"})` → 3개 모두 완료. `--apply` 없이 돌리면 미리보기에 개수가 나와 알아챌 수 있지만, 그대로 `--apply` 하면 진도표에 반영됨(반영 전 백업은 저장됨)
- **해결/조치**: `check_rule` 이 `unit`·`title` 이 둘 다 빈 기준과 모르는 키(오타)를 `ValueError` 로 거절(`_` 로 시작하는 메모 키는 허용). `main` 은 진도표에 연결하기 전에 모든 기준을 확인. 가짜 시험만 했고 실제 진도표로는 돌리지 않음
- **남은 것**(2026-11-27 검토 🟡): ① `check_rule` 이 `subject` 없는 규칙을 통과시켜 연결 뒤 `KeyError`(쓰기 전이라 데이터는 안전) ② 3) 기존 행 처리(`done_until_existing`)는 `exclusive` 를 무시해 하나 더 칠함 ③ 맨 윗단계 키 오타(`done_untill_new`)는 조용히 건너뜀 — 허용 목록 확인 권함
- **관련 파일**: `semester_rollover.py`(`check_rule`), `tests/test_semester_rollover.py`(`RuleCheckTests`)


### ISSUE-002: `/api/lessons` 가 '날짜 시각' 모양의 slot_date 에서 죽음 (2026-11-25, 2026-11-26 해결)
- **상태**: 🟢 해결됨 (T69)
- **증상**: 수업배치 시트의 `slot_date` 가 `2026-12-01 00:00:00` 처럼 시각이 붙어 있으면 `ValueError: 계획일 날짜 형식이 올바르지 않습니다` 가 `try` 밖에서 올라와 JSON 이 아닌 500 응답이 됐다.
- **원인**: `server.py` 는 `slot_date` 를 `[:10]` 으로 잘라 쓰려고 하지만, 그 앞의 정렬(`schedule._bridge_row_sort_key` → `_parse_date`)이 `YYYY-MM-DD` 만 받았다.
- **해결**: `server.py` 에 `_bridge_slot_sort_key` 를 두어 `YYYY-MM-DD` 뒤에 `공백·T + 숫자`(시각)가 붙은 모양만 날짜 부분으로 줄여 정렬한다. `2026. 12. 1.` 같은 다른 모양은 그대로 `schedule` 의 정렬이 읽는다(앞 10자를 무조건 자르면 깨지는 모양). 정렬 중 날짜를 도저히 못 읽으면 파이썬 오류 대신 JSON 오류(500)를 돌려준다. `schedule.py` 는 고치지 않음
- **시험**: `tests/test_server_lessons_catchup.py` — expectedFailure 표시를 지우고 시각 붙은 날짜·섞인 날짜 정렬·점 찍힌 날짜·읽을 수 없는 날짜 시험 추가. 소스를 일부러 틀리게 한 변이 3가지를 모두 시험이 잡음
- **남은 것**: 실제 시트에 시각이 붙는지는 확인 필요(교사 PC)
- **관련 파일**: `server.py`(`subject_lessons`, `_bridge_slot_sort_key`), `tests/test_server_lessons_catchup.py`

### ISSUE-001: `/api/catch-up` 가 시트 읽기 실패(ScheduleError)를 JSON 오류로 안 바꿈 (2026-11-25, 2026-11-26 해결)
- **상태**: 🟢 해결됨 (T69, `/api/catch-up` 만 — 나머지 경로는 ISSUE-005)
- **증상**: `schedule.connect()`·`load_all()` 이 `ScheduleError`(`SheetFormatError`·`ConfigurationError` 등)를 내면 `/api/catch-up` 은 처리하지 못하고 오류가 그대로 올라왔다(서버 500). 같은 서버의 `/api/lessons` 는 둘 다 잡아 JSON 오류를 돌려줬다.
- **원인**: `catch_up` 이 `except ValueError` 만 썼다. `ScheduleError` 는 `ValueError` 의 하위 클래스가 아니다.
- **해결**: `except schedule.ScheduleError` 를 `ValueError` 앞에 더해 JSON 오류(상태 500, 메시지는 오류 내용)로 돌려준다. `ValueError`(사용자가 고른 값 문제)는 그대로 400. 잠금(`_CATCH_UP_LOCK`) 안에서 일어나므로 잠금도 정상 해제됨
- **시험**: `tests/test_server_lessons_catchup.py` — expectedFailure 표시를 지우고 `connect`·`load_all` 에서 `SheetFormatError`·`ConfigurationError` 가 나는 경우, `ValueError` 는 여전히 400 인 시험 추가. 변이 2가지(안 잡기·400 으로 바꾸기) 모두 잡힘
- **관련 파일**: `server.py`(`catch_up`), `tests/test_server_lessons_catchup.py`

### ISSUE-004: /api/catch-up 동시 요청이 수업배치 갱신을 덮지 않도록 잠금 (2026-11-25)
- **상태**: 🟢 해결 (2026-11-25)
- **증상**: 동시에 들어온 두 요청이 같은 시트 내용을 읽고 각각 전체 수업배치를 다시 쓰면, 나중 저장이 먼저 저장한 변경을 덮을 수 있음
- **원인**: 읽기와 변경 작업을 묶어 보호하는 잠금이 없음
- **해결/조치**: `/api/catch-up` 의 시트 연결·읽기·변경 구간을 `threading.Lock` 으로 보호. 두 번째 요청은 첫 번째 작업이 끝난 뒤 최신 내용을 읽음. 두 요청을 동시에 보내도 작업 구간이 겹치지 않는 가짜 시험 추가
- **한계(검토 2026-11-26)**: 잠금은 `/api/catch-up` 에만 걸림. `/api/done`·push·extend·pull·move·swap 도 `_rewrite_bridge_sheet` → `write_bridge_sheet` 로 수업배치 전체를 다시 쓰므로, catch-up 과 미루기가 동시에 오면 여전히 덮일 수 있음 → 쓰기 경로 7개를 잠금 하나로 감싸는 후속 일(TASKS T77)
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
