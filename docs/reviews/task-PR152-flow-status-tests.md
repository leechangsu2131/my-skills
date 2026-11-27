# 검토: PR #152 — S1 `safe_name`·`flow_candidates`·`monitor_rects`·`prepare_status` 시험 (`a924186`)

claude-web-lee2131@hanmail · S2 · 2026-11-27 · 그 브랜치는 고치지 않고 보고만 함

## 결론: 합쳐도 됨 🟢 (🟡 하나: CI 가 이 시험 파일을 돌리지 않음)

시험 파일 하나(`skills/teacherlesson-assistant/test_assistant_flow_status.py`), ISSUES 한 항목, 일지만 바뀜. 코드는 안 건드림.

## 확인한 것
- 시험: 17 통과·1 expectedFailure (`pytest`, `unittest` 둘 다 같은 결과). 표준 라이브러리와 임시 폴더만 씀 — 실제 흐름·준비 상태 파일을 읽지 않음.
- **일부러 망가뜨려 시험이 잡는지 확인**(원래대로 돌리면 모두 통과):
  1. `safe_name` 길이 80 → 100: 실패 1
  2. 앞뒤 `_` 떼기 제거: 실패 1
  3. 경로 문자 `/`·`\` 치환 제거: 실패 4
  4. `flow_candidates` 가 `record_key` 를 정리 없이 쓰게: 실패 2 (폴더 밖으로 나가는 경로 시험이 잡음)
  5. `is_running` 에서 프로세스 생존 확인 제거: 실패 1
  6. `is_running` 의 '너무 오래됨' 확인 제거: 실패 2
- `monitor_rects` 시험: 리눅스(윈도우 API 없음)에서는 `(0,0,1920,1080,True)` 대체값을 확인하고, 윈도우에서는 모양만 확인하도록 갈라 둠. 가짜 ctypes 로 API 가 예외를 던져도 대체값이 나오는지도 확인 — 둘 다 코드와 맞음.
- ISSUES 의 새 항목(준비 상태 파일이 JSON 객체가 아니면 `AttributeError`): `prepare_status()` 가 `read_json` 결과를 dict 확인 없이 `is_running(status)` 에 넘기는 것이 코드(657~658줄)와 맞고, 재현 시험은 `expectedFailure`(strict 와 같은 효과: 고치면 '예상 밖 성공'으로 알려 줌).
- 개인정보·비밀값 모양 없음, 이름은 가짜.

## 🟡 알아 둘 점
1. **CI 가 이 파일을 안 돌린다.** `.github/workflows/check.yml` 의 수업 비서 `target` 은 `tests sites test_assistant_server.py test_supabase_schedule.py` 라서, 폴더 맨 위에 새로 둔 `test_assistant_flow_status.py` 는 PR 마다 도는 시험에 들어가지 않는다(같은 이유로 기존 `test_assistant_url_session.py` 도 빠져 있음 — 따로 확인 필요). 둘 중 하나로 풀 수 있음: ① 시험을 `tests/` 로 옮김(그 폴더는 `sys.path` 처리가 이미 되어 있음) ② `check.yml` target 에 파일 이름 추가(공용 파일이라 교사 PC 가 함).
2. `ISSUES.md` 의 항목 번호가 `ISSUE-새` — 합칠 때 번호를 붙여야 함(다른 PR 들도 같은 표기를 씀).

## 참고(고치라는 뜻 아님)
- `flow_candidates({"title": "분수"})` 처럼 `subject` 키가 없으면 `KeyError` 이지만, 호출하는 곳(`assistant_server.py` 228~229줄)이 `subject` 가 비어 있으면 먼저 거절하고 목록 쪽은 `subject` 기본값을 `""` 로 채워서 **지금 길로는 닿지 않음** — 시험이 이 경우를 안 다룬 것은 문제 아님.
