# claude-web-은정 일지

- 2026-11-26 20:27 T57 (teacherlesson-schedule) 시작 (브랜치 task/T57-schedule-easy-korean)
- 2026-11-26 20:29 T57 (teacherlesson-schedule) PR 올림 — SKILL.md 를 쉬운 한국어로 다시 쓰고 코드와 다른 곳(깨진 참고 링크·빠진 시험 파일·수업 비서와의 관계)을 바로잡음. 확인: 문서의 링크·파일 이름 존재, build_catalog --check 통과, 개인정보 검사. 시험은 문서만 고쳐 영향 없음(gspread·fitz 없는 환경이라 서버 시험은 못 돌림, 나머지 48개 실행 중 오류 2개는 fitz 없음 1 + 알려진 ISSUE-003 1). 범위 밖 발견(깨진 한글·requirements 누락)은 ISSUES 에만 기록 (브랜치 task/T57-schedule-easy-korean)
- 2026-11-26 20:30 T57 (teacherlesson-guide) 시작 (브랜치 task/T57-teacherlesson-guide-easy-korean)
- 2026-11-26 20:32 T57 (teacherlesson-guide) PR 올림 — SKILL.md 를 쉬운 한국어로 다시 쓰고, 옛 설명(진도 원본·다른 스킬 관계, 국어 학기 설정은 --subject 와 함께)을 코드에 맞춤, 시트 변경 경고 추가. 확인: 링크·파일 이름·명령 옵션 존재, build_catalog --check 통과, 개인정보 검사. 시험은 라이브러리가 없어 못 돌림(문서만 고침). ISSUES 2건 새로 기록. 참고: 앞 일 T57 진도 서버 브랜치 task/T57-schedule-easy-korean 은 이름에 스킬 이름 전체가 없어 claim_task --skill teacherlesson-schedule 확인에 안 걸림 — 이미 PR #89 있음 (브랜치 task/T57-teacherlesson-guide-easy-korean)
- 2026-11-26 20:32 T57 (util-notebooklm) 시작 (브랜치 task/T57-util-notebooklm-easy-korean)
- 2026-11-26 20:33 T57 (util-notebooklm) PR 올림 — SKILL.md 를 쉬운 한국어로 정리, 명령별 저장 위치·윈도우 전용·글자 적은 쪽 설명을 코드에 맞춤. 확인: 코드 대조, build_catalog --check, 개인정보 검사(tests/test_nlm.py 는 라이브러리가 없어 건너뜀) (브랜치 task/T57-util-notebooklm-easy-korean). 앞 PR #91 정정: 'pytest 못 돌림' 중 splitter 시험 10개는 splitter 폴더에서 통과함. 다음: T57 남은 묶음 스킬은 teacherlesson-assistant(다른 작업이 고치는 중일 수 있어 확인 필요) — 이후 상시 일(S) 또는 PR 검토(S2)
- 2026-11-27 06:45 S2 (batch) 시작 (브랜치 task/S2-review-batch-1127)
- 2026-11-27 06:47 S2 (batch) PR 올림 — #94·#95·#96·#97·#99·#100·#101 검토 7개, 모두 🟢(작은 의견 포함). 확인: 차례로 합쳐 일지 충돌만 확인, sites+ISSUE-043 시험 45 통과·2 건너뜀·1 xfail, #95 는 삭제 경로 차단·연락처 처리·남은 번호 모양·그림 일부 (브랜치 task/S2-review-batch-1127)
