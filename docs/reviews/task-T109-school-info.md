# 검토: task/T109-school-info (PR #181 — 🍱 급식·날씨 한 줄)

- 검토: claude · 2026-11-28 (상시 일 S2)
- 대상 커밋: `e725465` — main 기준 충돌 없음(단독)
- **판정: 🟡 고친 뒤 합치기 권함** — 설정 이름이 지금 TASKS 와 달라 교사 PC 에서 칸이 안 켜질 수 있음

## 🟡 고칠 것

- **환경 변수 이름이 어긋남.** 코드는 학교·교육청 코드를 `TEACHERLESSON_ASSISTANT__SCHOOL_CODE`·`__OFFICE_CODE`, 키를 `NEIS_OPEN_API_KEY` 로만 읽음(`school_info.py`). 그런데 현재 `docs/TASKS.md` T109 는 교사가 중앙 `.env` 에 **공용 키 `NEIS_SCHOOL_CODE`·`NEIS_OFFICE_CODE`·`NEIS_API_KEY`** 를 이미 넣었고 급식 조회가 된다고 적음(2026-11-28). 이 PR 은 그 줄이 바뀌기 전 문구를 따른 것으로 보임(추정). 그대로 합치면 교사 PC 에서 설정이 있는데도 칸이 숨음.
  - 권함: 공용 이름(`NEIS_SCHOOL_CODE`·`NEIS_OFFICE_CODE`·`NEIS_API_KEY`)을 먼저 읽고, 없으면 지금 이름을 읽기. 시험(`tests/test_school_info.py`)에 공용 이름 한 건, README 한 줄. 날씨 좌표(`…__LATITUDE`·`__LONGITUDE`)는 TASKS 에도 '좌표는 `.env`'라고만 있어 그대로 두어도 됨.

## 확인한 것

- 이 브랜치에서 `tests/test_school_info.py` 11개·`node tests/test_school_info.js` 6개 통과, 서버 시험 통과, 그 폴더 `pytest tests` 484 통과·기존 xfail 4.
- **키가 화면으로 새지 않음**: `/api/school-info` 응답은 `{status, date, meal, weather}` 뿐. 키는 요청 주소에만 쓰이고, 실패는 `except Exception` 으로 조용히 넘겨 로그에도 안 찍힘.
- 하루 한 번 캐시(`school_info_cache.json`, 데이터 폴더), 하나라도 실패하면 저장하지 않아 다음에 다시 시도, 시간 제한 4초, 설정이 없으면 칸을 숨김(오류 문구 없음).
- 급식 글 정리: `(5.6.13)` 같은 알레르기 번호를 지움(README 에도 적어 둠). 의도된 설계로 보임.

## 🟢/참고

- 알레르기 번호를 지우는 것은 한 줄 화면 정리용이라 괜찮아 보이나, 알레르기가 있는 학생이 있는 반이면 교사가 번호를 보고 싶을 수 있음(교사 판단).
- 실제 NEIS 급식 API·open-meteo 호출은 시험하지 못함(가짜 응답만). PR 설명대로 교사 PC 확인 필요.

## 다른 PR 과 함께 합칠 때

- #179(T106)와는 `assistant_server.py`·`web/index.html` 에서, #183(T107)과는 `assistant_server.py` 에서 줄이 겹쳐 충돌함(아래 '합치는 순서').
