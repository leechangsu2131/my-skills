# claude-web-은정 일지

- 2026-11-26 21:00 S2 (T82) 시작 (브랜치 task/S2-review-t82-sites-title-match)
- 2026-11-26 21:01 S2 (T82) PR 올림 — docs/reviews/task-T82-sites-title-match.md. 🔴 PR #87 그대로 합치면 앞의 비슷한 차시가 정확한 차시보다 먼저 골라짐(가짜 목록 사례 A·B·C 를 합치기 전/후 코드로 비교해 재현). 확인: sites 49 통과·3 건너뜀, 도우미 시험 12개(가짜 selenium) 통과, 개인정보 검사 0. 대상 브랜치는 고치지 않음 (브랜치 task/S2-review-t82-sites-title-match)
- 2026-11-27 06:34 S2 PR #87 고친 커밋(6b75290) 다시 검토 — 첫 재현 3건 해결, 남은 것 2개를 docs/reviews/…-recheck.md 에. 확인: PR 시험 44 통과(가짜 selenium)·pytest sites 63 통과 3 건너뜀·추가 사례 재현. 파일 이름은 main 의 같은 이름과 겹치지 않게 바꿈
