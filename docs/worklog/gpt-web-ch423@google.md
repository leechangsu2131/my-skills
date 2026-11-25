# gpt-web-ch423@google 일지

- 2026-11-25 22:45 T26 시작 (브랜치 task/T26-notebooklm-model-timeout)
- 2026-11-25 22:58 T26 PR 올림 — 모델별 대기 시간·실제 모델 반환·호출부 갱신, 가짜 subprocess 시험 보강. PR #26: pytest 성공, catalog 는 PyYAML 미설치로 실패. 기존 teacherlesson-schedule 시험 1개 실패(ISSUE-003)
- 2026-11-25 23:00 T27 시작 (브랜치 task/T27-catch-up-request-lock)
- 2026-11-25 23:05 T27 PR 올림 — /api/catch-up 시트 읽기·변경 구간 잠금, 동시 요청 가짜 시험 추가. PR #27: 새 시험 포함 83개 통과, 2 xfail, 기존 ISSUE-003 시험 1개 실패. catalog 는 PyYAML 미설치로 실패
- 2026-11-25 23:10 T28 시작 (브랜치 task/T28-supabase-schedule-lock)
- 2026-11-25 23:15 T28 PR 올림 — progress() 읽기·변경 잠금과 동시 완료 시험 추가, 프로세스 간 잠금 한계 기록. PR #28, 전용 시험 실행 중
- 2026-11-25 23:20 T29 시작 (브랜치 task/T29-assistant-favicon)
- 2026-11-25 23:30 T29 PR 올림 — favicon SVG·/favicon.ico 응답·화면 연결·가짜 HTTP 시험. PR #29, CI 확인 필요
- 2026-11-25 23:35 T29 CI 확인 — teacherlesson-assistant 시험 130개 통과, 개인정보·guide splitter 통과. catalog 는 PyYAML 미설치로 실패, known-failing 은 기존 ISSUE-003 1개 실패
