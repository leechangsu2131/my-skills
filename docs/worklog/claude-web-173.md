# claude-web-173 일지

- 2026-11-25 19:19 T45 시작 (브랜치 task/T45-fix-catchup-tests)
- 2026-11-25 19:24 T45 PR 올림 — CatchUpTest 를 새 동작(요청 날짜 칸으로 옮기기·sort_order 기준 앞 차시 완료)에 맞게 다시 씀. test_supabase_schedule.py 41개 중 39 통과·1 건너뜀(PyMuPDF 없음)·1 알려진 실패(ISSUE-033, 코드 문제라 고치지 않고 기록). 소스를 일부러 틀리게 한 변이 9가지를 모두 시험이 잡음. 이 스킬 시험 전체 71 통과, build_catalog --check 문제 없음
- 2026-11-26 04:50 T45 시작 — ISSUE-033 후속 (브랜치 task/T45-catchup-show-chosen-lesson, 교사가 '쓴다, 화면도 바뀌면 좋겠다'고 정함)
- 2026-11-26 04:55 T45 PR 올림 — day_schedule 이 따라잡기로 고른 예정 차시(manual_catch_up)를 먼저 보여 줌, LESSON_REL 에 source 추가. 시험 7개 추가·expectedFailure 제거, test_supabase_schedule.py 47 통과·1 건너뜀, 스킬 전체 150 통과. 변이 4가지 모두 잡힘. PR #15 위에 쌓은 PR
