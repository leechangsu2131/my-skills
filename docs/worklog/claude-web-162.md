# claude-web-162 일지

- 2026-11-25 19:15 T05 시작 (브랜치 task/T05-tests-supabase-export)
- 2026-11-25 19:30 T05 PR 올림 — tests/test_export.py 시험 25개(21 통과, 4 xfail), 소스 무변경, 버그 3건 ISSUES 기록
- 2026-11-25 19:40 T05 다음: T06 선택(personal-library-search 순수 함수 시험)
- 2026-11-25 19:41 T06 시작 (브랜치 task/T06-tests-library-search, T05 브랜치 위에서 만듦: 일지 파일 충돌 피하려고)
- 2026-11-25 20:05 T06 PR 올림 — tests/test_pure_functions.py 시험 27개(25 통과, 2 xfail), 소스 무변경, 문제 3건 ISSUES 기록(ISSUE-002~004). T05 브랜치 위에 쌓임
- 2026-11-25 20:20 T06 다음: T12 선택(personal-carrot 순수 함수 시험)
- 2026-11-25 20:21 T12 시작 (브랜치 task/T12-tests-carrot, T06 브랜치 위에서 만듦)
- 2026-11-25 20:50 T12 PR 올림 — personal-carrot tests/test_pure_functions.py 시험 71개(65 통과, 6 xfail), 소스 무변경, 문제 4건 ISSUES 기록. appium·selenium 은 설치돼 있지 않아 가짜 모듈로 대신. T06 브랜치 위에 쌓임
- 2026-11-25 21:05 (교사 요청) 노션 DB ID 노출 제거 시작 (브랜치 fix/library-sync-remove-db-id, T12 브랜치 위에서 만듦)
- 2026-11-25 21:25 노션 DB ID 제거 PR 올림 — 코드·.env.example 에서 ID 삭제, load_env() 로 중앙 .env 읽기, 시험 28개 통과(2 xfail), 값은 기록에 쓰지 않음. T12 브랜치 위에 쌓임
