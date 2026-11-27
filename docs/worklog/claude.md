# claude 일지

- 2026-11-27 04:08 S7 (util-notebooklm) 시작 (브랜치 task/S7-multi-pdf-find)
- 2026-11-27 04:14 S1 (teacherlesson-assistant) 시작 (브랜치 task/S1-url-session-tests)
- 2026-11-27 04:30 S7 (util-notebooklm) PR 올림 — ISSUE-004 '여러 PDF 한 번에 찾기'·'[p.N] 자동 대조' 설계 메모(skills/util-notebooklm/docs/plans/multi-pdf-find.md). 코드는 안 고침. 확인: nlm.py·tests/test_nlm.py 를 읽고 함수 이름·시험 모양 정함, build_catalog --check·check_privacy 통과(시험 코드는 없음)
- 2026-11-27 04:40 S1 (teacherlesson-assistant) PR 올림 — assistant_server.py 의 열 수 있는 주소 확인(ai_sites·allowed_urls·check_site_url)·저장 기록 일치 확인(session_matches_lesson·saved_mismatch_info) 시험 18개 새로 씀(test_assistant_url_session.py, 코드는 안 고침). 확인: 새 시험 18개 + 기존 test_assistant_server 합쳐 56개 통과, build_catalog --check·check_privacy 통과
- 2026-11-27 08:33 S1 (teacherlesson-assistant) 시작 (브랜치 task/S1-parse-plan-tests)
- 2026-11-27 05:05 S1 (teacherlesson-assistant) PR 올림 — prepare_lessons.parse_plan(수업 뼈대 검사) 시험 29개 새로 씀(tests/test_parse_plan.py). 시험 중 '음수 분 -5 를 5 로 읽음' 버그 발견 → xfail(strict) 재현 시험 + ISSUES.md 에 한 항목, 코드는 안 고침. 확인: 전체 pytest 423 통과·1 xfail(새 것), build_catalog --check·check_privacy 통과
