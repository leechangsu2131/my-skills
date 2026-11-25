# claude-소연 일지

- 2026-11-25 19:47 T46 시작 (브랜치 task/T46-check-setup-fixes)
- 2026-11-25 19:53 T46 PR 올림 — check_setup.py 보완 4가지(Python 실행기 py -3.13/python 둘 다 점검·버전 다르면 ⚠ / 5180 열려 있으면 HTTP 로 물어 수업 비서인지 확인 / port·debug_port 가 숫자 아니면 멈추지 않고 ❌ / schedule_backend 가 supabase 아니면 Supabase 키 없음 ⚠). 시험 47→106개 통과, 코드를 일부러 망가뜨린 변이 10개 모두 시험이 잡음. 점검_PC.bat·실행_수업비서.bat 은 윈도우에서 못 돌려 봐서 안 고침(ISSUE-034). 범위 밖 발견 ISSUE-035
- 2026-11-25 19:54 T11 시작 (브랜치 task/T11-tests-gbetalk)
- 2026-11-26 04:21 T11 PR 올림 — admin-gbetalk 쪽지 보관·정리 시험 112개(gbtalk_summary.py 보관·복구·중복·순서 안전장치, build_archive_input.py 입력 검증·병합). 가짜 자료·임시 폴더만 사용, 실제 데이터 폴더·발송·화면 조작 없음. 코드를 일부러 망가뜨린 변이 28개 모두 시험이 잡음. 같은 T11 을 gpt-web-ch423@google 이 00:06 에 따로 시작함(task/T11-admin-gbetalk-parser-tests) — 파일 이름 달라 충돌 없음, 그쪽 시험 1개는 혼자서도 실패(기대값 오류)
- 2026-11-26 04:22 T56 시작 (브랜치 task/T56-privacy-checklist)
- 2026-11-26 04:23 T56 PR 올림 — docs/PRIVACY_CHECKLIST.md 1쪽(올리기 전 30초 점검·조심할 파일·커밋 직전 순서·괜찮은 것·실수로 올렸다면). 근거는 WORKER_GUIDE §3(교사 결정 11-25)·SECURITY_LESSONS_LEARNED §2·5·6. check_privacy.py 가 이메일도 경고하는 것을 실행해 확인(교사 결정과 어긋남 → PR 에 적음)
- 2026-11-26 04:40 T55 시작 (브랜치 task/T55-glossary)
- 2026-11-26 04:41 T55 PR 올림 — docs/GLOSSARY.md 용어 사전(수업·진도 / lesson_id·record_key 구분 / 수업 비서 파일 / 학교 업무 / 저장소 규칙). 뜻은 SKILL.md·README·supabase_schedule.py 에서 확인한 것만, 모르는 것은 확인 필요 표시
