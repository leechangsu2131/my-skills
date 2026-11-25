# claude-web-173 일지

- 2026-11-25 19:19 T45 시작 (브랜치 task/T45-fix-catchup-tests)
- 2026-11-25 19:24 T45 PR 올림 — CatchUpTest 를 새 동작(요청 날짜 칸으로 옮기기·sort_order 기준 앞 차시 완료)에 맞게 다시 씀. test_supabase_schedule.py 41개 중 39 통과·1 건너뜀(PyMuPDF 없음)·1 알려진 실패(ISSUE-033, 코드 문제라 고치지 않고 기록). 소스를 일부러 틀리게 한 변이 9가지를 모두 시험이 잡음. 이 스킬 시험 전체 71 통과, build_catalog --check 문제 없음
- 2026-11-25 19:24 T47 시작 (브랜치 task/T47-memo-sync-fixes)
- 2026-11-26 04:12 T47 PR 올림 — memo_sync: 받은 메모에 서버 memo_key 저장·재사용(at 없는 메모 중복 해결), CLI 출력 UTF-8, 올리기 제외 종류 설정(MEMO_SKIP_KINDS, 학생 메모는 항상 제외), README·SKILL 사용법 절. tests/test_memo_sync.py 24→33개 통과, 변이 9가지 모두 시험이 잡음, build_catalog --check 문제 없음. 전체 시험의 실패 4개는 T45(PR #15) 대상으로 이 PR 과 무관
- 2026-11-26 04:13 T15 시작 (브랜치 task/T15-popup-pure-tests, 대상 teacherlesson-from-neis)
