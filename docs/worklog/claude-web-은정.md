# claude-web-은정 일지

- 2026-11-26 20:27 T57 (teacherlesson-schedule) 시작 (브랜치 task/T57-schedule-easy-korean)
- 2026-11-26 20:29 T57 (teacherlesson-schedule) PR 올림 — SKILL.md 를 쉬운 한국어로 다시 쓰고 코드와 다른 곳(깨진 참고 링크·빠진 시험 파일·수업 비서와의 관계)을 바로잡음. 확인: 문서의 링크·파일 이름 존재, build_catalog --check 통과, 개인정보 검사. 시험은 문서만 고쳐 영향 없음(gspread·fitz 없는 환경이라 서버 시험은 못 돌림, 나머지 48개 실행 중 오류 2개는 fitz 없음 1 + 알려진 ISSUE-003 1). 범위 밖 발견(깨진 한글·requirements 누락)은 ISSUES 에만 기록 (브랜치 task/T57-schedule-easy-korean)
- 2026-11-26 20:30 T57 (teacherlesson-guide) 시작 (브랜치 task/T57-teacherlesson-guide-easy-korean)
- 2026-11-26 20:32 T57 (teacherlesson-guide) PR 올림 — SKILL.md 를 쉬운 한국어로 다시 쓰고, 옛 설명(진도 원본·다른 스킬 관계, 국어 학기 설정은 --subject 와 함께)을 코드에 맞춤, 시트 변경 경고 추가. 확인: 링크·파일 이름·명령 옵션 존재, build_catalog --check 통과, 개인정보 검사. 시험은 라이브러리가 없어 못 돌림(문서만 고침). ISSUES 2건 새로 기록. 참고: 앞 일 T57 진도 서버 브랜치 task/T57-schedule-easy-korean 은 이름에 스킬 이름 전체가 없어 claim_task --skill teacherlesson-schedule 확인에 안 걸림 — 이미 PR #89 있음 (브랜치 task/T57-teacherlesson-guide-easy-korean)
