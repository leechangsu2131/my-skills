# claude 일지

- 2026-11-27 04:08 S7 (util-notebooklm) 시작 (브랜치 task/S7-multi-pdf-find)
- 2026-11-27 04:14 S1 (teacherlesson-assistant) 시작 (브랜치 task/S1-url-session-tests)
- 2026-11-27 04:30 S7 (util-notebooklm) PR 올림 — ISSUE-004 '여러 PDF 한 번에 찾기'·'[p.N] 자동 대조' 설계 메모(skills/util-notebooklm/docs/plans/multi-pdf-find.md). 코드는 안 고침. 확인: nlm.py·tests/test_nlm.py 를 읽고 함수 이름·시험 모양 정함, build_catalog --check·check_privacy 통과(시험 코드는 없음)
- 2026-11-27 04:40 S1 (teacherlesson-assistant) PR 올림 — assistant_server.py 의 열 수 있는 주소 확인(ai_sites·allowed_urls·check_site_url)·저장 기록 일치 확인(session_matches_lesson·saved_mismatch_info) 시험 18개 새로 씀(test_assistant_url_session.py, 코드는 안 고침). 확인: 새 시험 18개 + 기존 test_assistant_server 합쳐 56개 통과, build_catalog --check·check_privacy 통과
- 2026-11-27 09:10 S1 (teacherlesson-assistant) 시작 (브랜치 task/S1-transcribe-markdown-tests)
- 2026-11-27 07:25 S1 (teacherlesson-assistant) PR 올림 — transcribe.build_markdown(받아쓰기 결과 → 마크다운 글) 시험 10개 새로 씀(tests/test_transcribe_markdown.py), 코드는 안 고침. 확인: 그 폴더 unittest discover 93개 통과, 루트 pytest 395 통과, build_catalog --check·check_privacy 통과
