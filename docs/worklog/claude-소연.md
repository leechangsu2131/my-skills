# claude-소연 일지

- 2026-11-25 19:47 T46 시작 (브랜치 task/T46-check-setup-fixes)
- 2026-11-25 19:53 T46 PR 올림 — check_setup.py 보완 4가지(Python 실행기 py -3.13/python 둘 다 점검·버전 다르면 ⚠ / 5180 열려 있으면 HTTP 로 물어 수업 비서인지 확인 / port·debug_port 가 숫자 아니면 멈추지 않고 ❌ / schedule_backend 가 supabase 아니면 Supabase 키 없음 ⚠). 시험 47→106개 통과, 코드를 일부러 망가뜨린 변이 10개 모두 시험이 잡음. 점검_PC.bat·실행_수업비서.bat 은 윈도우에서 못 돌려 봐서 안 고침(ISSUE-034). 범위 밖 발견 ISSUE-035
- 2026-11-26 04:40 T55 시작 (브랜치 task/T55-glossary)
- 2026-11-26 04:41 T55 PR 올림 — docs/GLOSSARY.md 용어 사전(수업·진도 / lesson_id·record_key 구분 / 수업 비서 파일 / 학교 업무 / 저장소 규칙). 뜻은 SKILL.md·README·supabase_schedule.py 에서 확인한 것만, 모르는 것은 확인 필요 표시
