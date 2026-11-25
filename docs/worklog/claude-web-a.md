# claude-web-a 일지

- 2026-11-25 19:30 T04 시작 (브랜치 task/T04-tests-schedule-server)
- 2026-11-25 20:05 T04 PR 올림 — skills/teacherlesson-schedule/tests/test_server_lessons_catchup.py 시험 30개(28 통과, 2 xfail). 확인: pytest 로 이 스킬 시험 실행. 버그 후보 2개를 ISSUES(ISSUE-001·002)에 기록·xfail, 원래부터 실패하는 test_auto_planner 1개는 ISSUE-003 에 기록(고치지 않음)
- 2026-11-25 20:20 T23 시작 (브랜치 task/T23-github-actions-check)
- 2026-11-25 20:50 T23 PR 올림 — .github/workflows/check.yml 새로 추가(catalog 점검·T22 개인정보 검사(파일 있을 때만)·깨끗한 환경에서 통과 확인한 시험 2개 스킬·알려진 실패 1개 스킬은 막지 않고 표시). 확인: YAML 문법, 각 단계 로컬 모의 실행, 가짜 키 탐지(종료 코드 1). 실제 GitHub 에서 돌려 보기는 PR 에서 확인 필요
- 2026-11-25 21:10 T09 시작 (브랜치 task/T09-tests-obsidian-pkm)
- 2026-11-25 22:10 T09 PR 올림 — skills/personal-obsidansystem-main/tests/test_pkm_core.py 시험 81개(77 통과, 4 xfail), 실제 볼트·백업 폴더 안 건드림(백업 위치를 임시 폴더로 바꿈). 확인: pytest 실행, 가려 보이는 xfail 4개는 표시를 떼고 의도한 이유로 실패하는지 확인. 버그 3개(쉼표 목록·큰따옴표 역슬래시 누적·Vault 폴더 이름)를 ISSUES(ISSUE-002~004)에 기록
