# 설계 메모: 수업배치 쓰기 경로 7개를 잠금 하나 + 오류 처리 하나로 (S7)

작성: claude-web-173 · 2026-11-27 · 대상: `skills/teacherlesson-schedule/server.py` · 관련: ISSUE-004(한계)·ISSUE-005, TASKS T77(P)
**코드는 고치지 않았다.** 이 메모는 T77 을 하는 교사 PC 작업자가 그대로 따라 하라고 쓴 것이다.

## 1. 지금 상태

| 경로 | 함수(줄) | 잠금 | `ScheduleError`→JSON | 날짜 파싱 위치 |
|---|---|---|---|---|
| `/api/catch-up` | `catch_up` (572) | ✅ `_CATCH_UP_LOCK` | ✅ (500) | — |
| `/api/done` | `done` (461) | ❌ | ❌ | `try` 밖(`date.fromisoformat`) |
| `/api/push` | `push` (493) | ❌ | ❌ | `try` 밖 |
| `/api/extend` | `extend` (517) | ❌ | ❌ | (확인 필요) |
| `/api/pull` | `pull` (554) | ❌ | ❌ | — |
| `/api/move` | `move` (602) | ❌ | ❌ | — |
| `/api/swap` | `swap` (621) | ❌ | ❌ | — |

- 7개 모두 "시트 연결 → 전체 읽기(`load_all`) → 바꾸기 → 수업배치 전체를 다시 쓰기(`_rewrite_bridge_sheet`→`write_bridge_sheet`)" 순서다. 두 요청이 겹치면 나중 저장이 먼저 저장을 덮는다(ISSUE-004 한계).
- 개발 서버는 `app.run(port=5000, debug=True)`(695줄) — Flask 기본이 스레드 하나씩이라 **동시 요청이 실제로 겹친다**(브라우저 두 탭·더블클릭).
- 재현 시험은 이미 있다: `tests/test_server_write_routes_schedule_error.py`(S3, 6개 expectedFailure).

## 2. 만들 것 (server.py 안에서만)

1. 이름 정리 — `_CATCH_UP_LOCK` → `_SHEET_WRITE_LOCK`(같은 `threading.Lock()`). 기존 시험이 `_CATCH_UP_LOCK` 을 가리키면 `_CATCH_UP_LOCK = _SHEET_WRITE_LOCK` 별칭을 한 줄 남긴다(`grep -rn _CATCH_UP_LOCK tests` 로 확인).
2. 데코레이터 하나(`_action_error` 바로 아래):

```python
def _sheet_write(view):
    """수업배치를 다시 쓰는 요청: 잠금 안에서 실행하고 시트 오류를 JSON 으로 바꾼다."""
    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        with _SHEET_WRITE_LOCK:
            try:
                return view(*args, **kwargs)
            except schedule.ScheduleError as exc:   # ValueError 의 하위가 아님 → 먼저 잡는다
                return _action_error(str(exc), 500)
            except ValueError as exc:
                return _action_error(str(exc))
    return wrapper
```

3. 7개 라우트에 `@app.route(...)` **아래** `@_sheet_write` 를 붙이고, 각 함수 안의 `try/except ValueError` 는 지운다(오류를 데코레이터가 처리). `catch_up` 의 `with _CATCH_UP_LOCK:` 블록도 걷어낸다.
4. 성공 뒤의 `log_action(...)`·`_clear_dashboard_cache()`·`_action_success(...)` 는 잠금 안에 둔다(짧고, 순서가 뒤바뀌어 오래된 캐시가 남는 것을 막는다).

### 지켜야 할 것
- **데코레이터는 `@app.route` 보다 아래**여야 한다(위에 두면 Flask 에 감싸기 전 함수가 등록됨).
- `functools.wraps` 가 없으면 Flask 가 엔드포인트 이름을 모두 `wrapper` 로 보아 "Endpoint 중복" 오류가 난다.
- 잠금 안에서 응답을 만든 뒤 **밖에서** 느린 일(PDF 열기·네트워크)을 하지 않는다. 지금 7개는 시트 호출뿐이라 괜찮다.
- 지금 `done`·`push` 의 `date.fromisoformat` 은 `try` 밖이라 잘못된 날짜는 파이썬 오류 화면(500 HTML)이다. 데코레이터 안으로 들어오면 400 JSON 으로 **바뀐다** — 의도한 개선이므로 시험에 한 줄 넣는다.
- `GET /api/lessons`·`/api/dashboard` 는 잠그지 않는다(읽기만; 쓰는 중에 읽으면 직전 상태가 보일 수 있으나 시트 자체는 안 깨진다 — 추정). 막으려면 따로 결정.
- 이 잠금은 **한 서버 프로세스 안에서만** 막는다. `schedule.py` 를 명령줄로 따로 돌리거나 서버를 둘 띄우면 못 막는다(범위 밖, ISSUE 에 한 줄).

## 3. 시험 (`tests/`)

기존 `tests/test_server_lessons_catchup.py` 의 동시 요청 시험(ISSUE-004) 방식을 그대로 쓴다.

1. `tests/test_server_write_routes_schedule_error.py` — expectedFailure 6개 표시를 모두 지운다(고치면 "예상 밖 성공"이 나므로 표시를 안 지우면 시험이 실패해 알려 준다).
2. **섞인 동시 요청** — `catch_up` 과 `push`(또는 `done`)를 두 스레드로 동시에 보내고, 가짜 `schedule.connect`/`load_all`/쓰기 함수 안에서 "지금 안에 있는 요청 수"를 세어 **최대 1** 임을 확인(7개 라우트를 `subTest` 로 돌려 모두 확인). 잠금을 뺀 변이에서 실패해야 한다.
3. **잠금 해제 확인** — 첫 요청이 `ScheduleError`/`ValueError`/예외로 끝나도 두 번째 요청이 막히지 않는다(`with` 라 자동이지만 회귀 방지).
4. `done`·`push` 에 `from_date="아님"` → 400 JSON.
5. 변이 확인: ① 데코레이터에서 `with` 제거 → 2번 실패, ② `ScheduleError` 잡기 제거 → expectedFailure 대신 정상 시험 실패, ③ `ValueError` 400 → 500 → 기존 400 시험 실패.

## 4. 문서·마무리
- `ISSUES.md`: ISSUE-004 한계 문구와 ISSUE-005 를 🟢 로 옮긴다(시험 이름 적기).
- `python tools/build_catalog.py --check`, `git diff --staged | python tools/check_privacy.py --stdin`.
- T77 은 **P**(교사 PC)다. 실제 시트로 두 탭에서 동시에 [미루기]·[따라잡기]를 눌러 보는 확인은 교사 PC 에서 한다(웹 작업자는 가짜 시트 시험까지).

## 5. 크기·위험
- 고칠 파일 `server.py` 1개 + 시험 2개. 줄 수는 대략 +20/-60.
- 위험: 라우트 안쪽 오류 처리를 걷어내다 `return` 위치가 바뀌는 실수 — 라우트마다 기존 시험(`tests/test_server.py`)을 먼저 돌려 둔다.

## 6. 확인 못 한 것
- `extend`·`pull`·`move`·`swap` 안의 날짜 파싱 위치와 각 함수 안쪽 오류 처리는 줄 단위로 다 읽지 않았다(확인 필요).
- 실제 시트에서의 겹침 재현은 하지 않았다.
