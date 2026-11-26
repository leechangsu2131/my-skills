# claude-web-은정 일지

- 2026-11-26 20:27 T57 (teacherlesson-schedule) 시작 (브랜치 task/T57-schedule-easy-korean)
- 2026-11-26 20:29 T57 (teacherlesson-schedule) PR 올림 — SKILL.md 를 쉬운 한국어로 다시 쓰고 코드와 다른 곳(깨진 참고 링크·빠진 시험 파일·수업 비서와의 관계)을 바로잡음. 확인: 문서의 링크·파일 이름 존재, build_catalog --check 통과, 개인정보 검사. 시험은 문서만 고쳐 영향 없음(gspread·fitz 없는 환경이라 서버 시험은 못 돌림, 나머지 48개 실행 중 오류 2개는 fitz 없음 1 + 알려진 ISSUE-003 1). 범위 밖 발견(깨진 한글·requirements 누락)은 ISSUES 에만 기록 (브랜치 task/T57-schedule-easy-korean)
- 2026-11-26 20:30 T57 (teacherlesson-guide) 시작 (브랜치 task/T57-teacherlesson-guide-easy-korean)
- 2026-11-26 20:32 T57 (teacherlesson-guide) PR 올림 — SKILL.md 를 쉬운 한국어로 다시 쓰고, 옛 설명(진도 원본·다른 스킬 관계, 국어 학기 설정은 --subject 와 함께)을 코드에 맞춤, 시트 변경 경고 추가. 확인: 링크·파일 이름·명령 옵션 존재, build_catalog --check 통과, 개인정보 검사. 시험은 라이브러리가 없어 못 돌림(문서만 고침). ISSUES 2건 새로 기록. 참고: 앞 일 T57 진도 서버 브랜치 task/T57-schedule-easy-korean 은 이름에 스킬 이름 전체가 없어 claim_task --skill teacherlesson-schedule 확인에 안 걸림 — 이미 PR #89 있음 (브랜치 task/T57-teacherlesson-guide-easy-korean)
- 2026-11-26 20:32 T57 (util-notebooklm) 시작 (브랜치 task/T57-util-notebooklm-easy-korean)
- 2026-11-26 20:33 T57 (util-notebooklm) PR 올림 — SKILL.md 를 쉬운 한국어로 정리, 명령별 저장 위치·윈도우 전용·글자 적은 쪽 설명을 코드에 맞춤. 확인: 코드 대조, build_catalog --check, 개인정보 검사(tests/test_nlm.py 는 라이브러리가 없어 건너뜀) (브랜치 task/T57-util-notebooklm-easy-korean). 앞 PR #91 정정: 'pytest 못 돌림' 중 splitter 시험 10개는 splitter 폴더에서 통과함. 다음: T57 남은 묶음 스킬은 teacherlesson-assistant(다른 작업이 고치는 중일 수 있어 확인 필요) — 이후 상시 일(S) 또는 PR 검토(S2)
- 2026-11-26 21:00 S2 (T82) 시작 (브랜치 task/S2-review-t82-sites-title-match)
- 2026-11-26 21:01 S2 (T82) PR 올림 — docs/reviews/task-T82-sites-title-match.md. 🔴 PR #87 그대로 합치면 앞의 비슷한 차시가 정확한 차시보다 먼저 골라짐(가짜 목록 사례 A·B·C 를 합치기 전/후 코드로 비교해 재현). 확인: sites 49 통과·3 건너뜀, 도우미 시험 12개(가짜 selenium) 통과, 개인정보 검사 0. 대상 브랜치는 고치지 않음 (브랜치 task/S2-review-t82-sites-title-match)
- 2026-11-27 06:34 S2 PR #87 고친 커밋(6b75290) 다시 검토 — 첫 재현 3건 해결, 남은 것 2개를 docs/reviews/…-recheck.md 에. 확인: PR 시험 44 통과(가짜 selenium)·pytest sites 63 통과 3 건너뜀·추가 사례 재현. 파일 이름은 main 의 같은 이름과 겹치지 않게 바꿈
- 2026-11-27 06:38 S2 (t91) 시작 (브랜치 task/S2-review-t91-enter-default)
- 2026-11-27 06:39 S2 (T91) PR 올림 — docs/reviews/task-T91-enter-default.md, 🟢 합치기 권함(🟡 2개). 확인: mapper 시험 main 26 통과 2 실패 → PR 34 통과 2 실패(가짜 모듈), 가짜 시트로 올리기 한 번, 개인정보 검사 (브랜치 task/S2-review-t91-enter-default)
- 2026-11-27 06:44 S2 (T82) 교사 결정 기록 — 못 찾을 때는 띄어쓰기·기호만 다른 것만 자동, 나머지 확인(나). 검토 파일에 반영, PR #87 에 댓글. 참고(T92 용): 교사 계정의 진도표 파일 휴업일 탭 첫 열 제목은 '날짜'(첫 몇 줄 읽기만), 날짜 모양 '2026. 3. 2' 는 fetch_holidays 가 main 에서 읽음(가짜 시트). 코드가 쓰는 파일과 같은지는 추정
- 2026-11-27 06:45 S2 (batch) 시작 (브랜치 task/S2-review-batch-1127)
- 2026-11-27 06:47 S2 (batch) PR 올림 — #94·#95·#96·#97·#99·#100·#101 검토 7개, 모두 🟢(작은 의견 포함). 확인: 차례로 합쳐 일지 충돌만 확인, sites+ISSUE-043 시험 45 통과·2 건너뜀·1 xfail, #95 는 삭제 경로 차단·연락처 처리·남은 번호 모양·그림 일부 (브랜치 task/S2-review-batch-1127)
