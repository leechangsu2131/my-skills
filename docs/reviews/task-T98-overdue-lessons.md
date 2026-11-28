# 검토: task/T98-overdue-lessons (PR #174)

- 검토: claude-web-yi2131@naver · 2026-11-28 (상시 일 S2)
- 대상: PR 머리 `415de7b` — main 기준. 이 브랜치는 고치지 않았음
- **판정: 🔴 이대로는 합치지 말 것 — main 에 T98 이 이미 다른 구현으로 들어와 있어 중복이고 충돌함**

## 왜 🔴 인가

- main 에는 T98(지난 미완료 차시 알림)이 **이미 합쳐졌음**: `95d9c43`(2026-11-27 21:21, `supabase_schedule.overdue_planned`·`state()["overdue"]`·`web/overdue.js`)과 `60300d8`(merge)·TASKS 에도 T98 "완료". 이 PR 은 같은 일을 이름만 다르게(`overdue`·`fetch_overdue`) 한 번 더 구현함.
- GitHub 도 `mergeable=false`. `git merge-tree` 로 보면 `ISSUES.md`·`assistant_server.py`·`supabase_schedule.py`·`tests/test_issue_repros.py`·`web/index.html`·`web/overdue.js`(양쪽이 새로 만든 파일) 등 7곳 충돌.
- 합치면 `/api/state` 의 `overdue` 칸 모양도 달라짐(main: `original_date`·`original_period`, 이 PR: `planned_date`·`period`) → 화면 코드와 어긋남.

## 확인한 것 (이 PR 자체의 품질은 좋음)

- 브랜치에서 `tests` 409 통과(이 브랜치가 오래된 main 에서 갈라져 main 의 473보다 적음), `test_overdue.js` 16 통과. 개인정보·비밀값 없음.
- 소스를 10곳 깨뜨려 보니 **10곳 모두** 시험이 잡음(날짜 범위 `lt`→`lte`, 상태, 14일 창, 같은 차시 중복 제거 방향, 30개 한도, 키 없는 슬롯, 오늘 교시 제외, 다른 백엔드, 실패 시 빈 목록, `state()` 연결).
- 읽기만 함(DB 를 바꾸지 않음), 가져오기는 기존 확인 창(`📍 실제로 할 차시 고르기`·`🏫 과목·차시 바꾸기`)을 그대로 불러서 자동 변경 없음 — 설계도 안전함.

## 🟡 main 구현에 없는 것 — 가져올 만함

main 의 `overdue_planned` 는 날짜가 오늘보다 앞선 `planned` 슬롯을 **전부** 읽음(창·중복 제거·한도 없음). 이 PR 의 안전장치가 필요할 수 있음:

1. 14일 창(`OVERDUE_DAYS_BACK`) — 학기 초에 옮기고 남은 옛 `planned` 슬롯이 계속 떠 있는 것을 막음(실제 데이터에 그런 슬롯이 있는지는 **확인 필요**).
2. 같은 차시가 여러 슬롯에 남았을 때 가장 최근 하나만.
3. 최대 30개.
4. 시험 14개(`tests/test_overdue_lessons.py`) — main 에는 `overdue_planned` 함수 자체를 직접 시험하는 것이 없고 `test_issue_repros.py` 2개로만 확인함.

## 권함

1. **#174 는 닫고**, 필요하면 위 1~4 를 main 위에서 `overdue_planned` 에 더하는 작은 PR 을 새로(시험 포함) 올리기. 작성 일이 겹치지 않게 TASKS 에 한 줄(예: T98 보강)을 교사가 열어 주면 좋음.
2. 한 번 더 같은 일이 겹치지 않도록: 이 PR 은 T98 "완료" 표시 **전**(2026-11-28 06:27)에 올라온 것으로 보이나 일지 시작 시각은 확인 못 함.

## 확인 못 한 것

- 진짜 Supabase 의 `and=(slot_date.gte…,slot_date.lt…)` 조회(가짜로만 시험함), 브라우저 클릭 흐름(점검표 8-8~8-11, 교사 PC).
