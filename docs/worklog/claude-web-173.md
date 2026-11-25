# claude-web-173 일지

- 2026-11-25 19:19 T45 시작 (브랜치 task/T45-fix-catchup-tests)
- 2026-11-25 19:24 T45 PR 올림 — CatchUpTest 를 새 동작(요청 날짜 칸으로 옮기기·sort_order 기준 앞 차시 완료)에 맞게 다시 씀. test_supabase_schedule.py 41개 중 39 통과·1 건너뜀(PyMuPDF 없음)·1 알려진 실패(ISSUE-033, 코드 문제라 고치지 않고 기록). 소스를 일부러 틀리게 한 변이 9가지를 모두 시험이 잡음. 이 스킬 시험 전체 71 통과, build_catalog --check 문제 없음
- 2026-11-26 05:05 T50 시작 (브랜치 task/T50-teacher-guide)
- 2026-11-26 05:15 T50 PR 올림 — teacherlesson-assistant README.md 에 '교사용 사용 설명서 (한 장)' 추가(날짜·교시 → 🌙 수업 준비 → 지금 할 일 → 메모 → 진도 조정, 그림 없이 쉬운 말), SKILL.md 에 안내 한 줄. 단추 이름·확인 창은 web/index.html 과 대조. 옛 이름 '여기부터 다시 잡기'를 화면 이름으로 표시. build_catalog --check 문제 없음
