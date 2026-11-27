# 검토: PR #139 — S7 설계 메모 "수업배치 쓰기 경로 7개를 잠금 하나 + 오류 처리 하나로" (`0cd2923`)

claude-web-lee2131@hanmail · S2 · 2026-11-27 · 코드는 고치지 않고 보고만 함

## 결론: 합쳐도 됨 🟢 (고칠 점 두 개는 🟡, T77 하는 사람이 알면 됨)

글 한 편(`docs/plans/teacherlesson-schedule-write-lock.md`)과 일지 한 줄만 바뀐 문서 PR. 코드·시험은 건드리지 않음.

## 코드와 대조한 것 (현재 main 기준)
- 7개 쓰기 경로와 줄 번호가 모두 맞음: `done` 461, `push` 493, `extend` 517, `pull` 554, `catch_up` 572, `move` 602, `swap` 621. `POST` 라우트는 이 7개뿐(빠진 쓰기 경로 없음).
- `_CATCH_UP_LOCK`(20줄)은 `catch_up` 에서만 쓰이고 `ScheduleError` 도 `catch_up` 에서만 잡음. 나머지 6개는 `except ValueError` 만 있음 — 표 내용 맞음.
- `ScheduleError` 는 `schedule.py` 85줄에서 `Exception` 을 직접 이어받음(`ValueError` 아님) → "먼저 잡는다"는 설명 맞음.
- `done`·`push` 의 `date.fromisoformat` 이 `try` 밖(467·498줄)이라 잘못된 날짜가 HTML 500 이 된다는 설명 맞음. `extend` 는 `int()` 변환이 `try` 안이라 이미 400 JSON — 메모의 "(확인 필요)" 칸은 **이미 안전**으로 채울 수 있음.
- `app.run(port=5000, debug=True)` 695줄 맞음. `_action_error`·`_action_success`·`log_action`·`_clear_dashboard_cache` 이름·모양 맞음.
- 7개 모두 결국 수업배치를 다시 쓰는 길임: `catch_up`·`move`·`pull`·`swap` 은 `_rewrite_bridge_sheet` 를 직접 부르고, `done`·`push`·`extend` 는 `_*_via_bridge` 를 거침(`schedule.py` 대조). 메모의 "전체 다시 쓰기" 설명 맞음.
- `tests/` 어디에도 `_CATCH_UP_LOCK` 이름이 없음 → 메모의 "별칭 한 줄" 은 **필요 없을 가능성이 높음**(`grep` 결과 0건, 메모가 확인하라고 한 그대로).
- 기존 재현 시험 `tests/test_server_write_routes_schedule_error.py`(7곳 `expectedFailure` 글자, 실제 시험 6개 — 하나는 import 줄)와 `test_server_lessons_catchup.py` 의 동시 요청 시험(`ThreadPoolExecutor`) 모두 있음.
- 개인정보·비밀값 모양 없음.

## 🟡 고칠 점
1. **`import functools` 가 빠져 있음.** 메모의 데코레이터는 `functools.wraps` 를 쓰는데 `server.py` 첫 줄 import 에 `functools` 가 없다(1~13줄 확인). "지켜야 할 것" 에 한 줄로 적어 두면 T77 이 `NameError` 로 헤매지 않음.
2. **동작이 조금 더 바뀌는 점을 적어 두면 좋음.** 데코레이터가 뷰 전체를 감싸므로 ① `ValueError` 를 잡는 범위가 `try` 안쪽에서 뷰 전체(`log_action`·응답 만들기 포함)로 넓어지고 ② `catch_up` 은 지금 `log_action`·캐시 비우기·응답 만들기가 잠금 **밖**인데 잠금 **안**으로 들어옴(메모 2-4가 이미 적었으니 의도 맞음). 첫째 항목만 "잠금 밖 → 안" 옆에 "ValueError 범위도 넓어짐" 한 줄이 있으면 더 분명함.
3. 5번째 시험 변이(③ `ValueError` 400 → 500)는 "기존 400 시험 실패"라고 했는데, `done`·`push` 의 **날짜 오류 400** 은 이번에 새로 생기는 것이라 기존 시험이 아님 — 4번 시험의 새 400 시험을 가리키는 것으로 고쳐 읽으면 맞음(작은 표현 문제).

## 참고
- 메모의 "Flask 기본이 스레드 하나씩" 은 "요청마다 스레드(threaded=True 기본)"라는 뜻으로 읽으면 맞음 — 결론(두 요청이 실제로 겹침)은 같음.
- 범위 밖 한계(서버를 둘 띄우거나 `schedule.py` 명령줄을 따로 돌리면 못 막음)도 메모에 이미 적혀 있음.
- 실제 시트로 두 탭 동시 누르기는 교사 PC(T77 은 P 등급)에서 확인해야 함 — 메모가 이미 밝힘.
