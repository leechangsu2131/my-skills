# claude 일지

- 2026-11-27 04:08 S7 (util-notebooklm) 시작 (브랜치 task/S7-multi-pdf-find)
- 2026-11-27 04:14 S1 (teacherlesson-assistant) 시작 (브랜치 task/S1-url-session-tests)
- 2026-11-27 04:30 S7 (util-notebooklm) PR 올림 — ISSUE-004 '여러 PDF 한 번에 찾기'·'[p.N] 자동 대조' 설계 메모(skills/util-notebooklm/docs/plans/multi-pdf-find.md). 코드는 안 고침. 확인: nlm.py·tests/test_nlm.py 를 읽고 함수 이름·시험 모양 정함, build_catalog --check·check_privacy 통과(시험 코드는 없음)
- 2026-11-27 04:40 S1 (teacherlesson-assistant) PR 올림 — assistant_server.py 의 열 수 있는 주소 확인(ai_sites·allowed_urls·check_site_url)·저장 기록 일치 확인(session_matches_lesson·saved_mismatch_info) 시험 18개 새로 씀(test_assistant_url_session.py, 코드는 안 고침). 확인: 새 시험 18개 + 기존 test_assistant_server 합쳐 56개 통과, build_catalog --check·check_privacy 통과
- 2026-11-27 06:45 fix/parse-flow-negative-minutes PR 올림 — 교사 요청: parse_flow(옛 경로)가 음수 분(-5)을 5분으로 읽던 것 고침(음수는 0). 시험 tests/test_parse_flow_minutes.py(고치기 전 4개 실패 확인). 전체 pytest 410 통과, build_catalog --check·check_privacy 통과
