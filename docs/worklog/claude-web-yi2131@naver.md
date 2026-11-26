# claude-web-yi2131@naver 일지

- 2026-11-25 19:29 T07 시작 (브랜치 task/T07-tests-storagemap)
- 2026-11-25 19:31 T07 PR 올림 — skills/util-storagemap/tests/server_helpers.test.js (시험 51개: 통과 49·todo 2·실패 0, server.js 를 잠깐 바꿔 시험이 잡아내는지 확인 후 되돌림), 확인 필요 3건 ISSUES 기록
- 2026-11-25 19:33 T08 시작 (브랜치 task/T08-tests-pdf-translator)
- 2026-11-25 19:36 T08 PR 올림 — skills/util-pdf-translator/tests/test_scripts.py (시험 102개: 통과 97·xfail 5·실패 0, 소스를 잠깐 바꿔 시험이 잡아내는지 확인 후 되돌림), 버그 후보 4건 + 확인 필요 3건(저작물 포함 교사 결정) ISSUES 기록
- 2026-11-26 04:13 T13 시작 — util-webtoguide 부분 (브랜치 task/T13-tests-webtoguide)
- 2026-11-26 04:15 T13(util-webtoguide) PR 올림 — skills/util-webtoguide/tests/test_webtoguide.py (시험 35개: 통과 31·xfail 4·실패 0, 소스를 잠깐 바꿔 시험이 잡아내는지 확인 후 되돌림), 버그 후보 3건 + 확인 필요 1건 ISSUES 기록. T13 의 workflow-hub-main·util-web-scraper 는 아직 안 함
- 2026-11-26 04:33 T13(util-webtoguide) 교사 지시 반영 — 결과물은 저장소에 저장하지 않음: webtoguide.py 가 data_dir() 에 저장, output/ 20개 추적 해제, .gitignore·SKILL.md·시험 반영 (시험 36개: 통과 32·xfail 4)
- 2026-11-26 04:34 T13 시작 — util-web-scraper 부분 (브랜치 task/T13-tests-web-scraper)
- 2026-11-26 04:35 T13(util-web-scraper) PR 올림 — skills/util-web-scraper/tests/test_add_urls.py (시험 17개: 통과 14·xfail 3·실패 0, 소스를 잠깐 바꿔 시험이 잡아내는지 확인 후 되돌림), 버그 후보 3건 + 확인 필요 1건(EduSearch 경로 고정) ISSUES 기록. T13 의 workflow-hub-main 은 아직 안 함
- 2026-11-26 05:07 T13(util-web-scraper) 교사 요청 반영 — EduSearch 고정 경로를 my-skills 옆 폴더(또는 .env UTIL_WEB_SCRAPER__EDUSEARCH_DIR)로 찾게 고침, 명령줄 시험 추가 (시험 30개: 통과 27·xfail 3). 교사 PC 에서 폴더 배치 확인 필요
- 2026-11-26 10:05 T60 시작 (브랜치 task/T60-safe-int-float)
- 2026-11-26 10:06 T60 PR 올림 — teacherlesson-workspace `sync_semester2.safe_int` 이 `12.0` 을 정수로 읽게 고침, xfail 해제 + 시험 추가 (tests/test_sync_semester2.py 23개 통과, 옛 소스로 되돌리면 3개 실패 확인 후 복구), ISSUE-T14 🟢. 범위 밖 같은 모양 `_safe_int` 2곳은 ISSUES 에 기록
- 2026-11-26 10:06 T63 시작 (브랜치 task/T63-library-xfail)
- 2026-11-26 10:07 T63 PR 올림 — personal-library-search xfail 2개를 소스를 고쳐 풀음: `_title_score` 를 순서를 보는 LCS 방식으로, `parse_text_file` 이 URL 앞 글을 제목에 합치게 (tests 34개 통과, 옛 소스로 되돌리면 5개 실패 확인 후 복구), ISSUE-002·003 🟢. 교사 PC 에서 books.txt 모양·교보 검색 결과 확인 필요
