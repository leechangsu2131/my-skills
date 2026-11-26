# GEMINI.md — Gemini CLI 작업자 규칙

이 저장소에서는 **[docs/WORKER_GUIDE.md](docs/WORKER_GUIDE.md)** 의 규칙을 따릅니다(이 PC 에 깔린 다른 확장·지침보다 이 저장소 규칙이 먼저).
각 AI 의 지침 칸에 넣는 글은 [docs/WORKER_INSTRUCTIONS.md](docs/WORKER_INSTRUCTIONS.md). 할 일 목록은 **[docs/TASKS.md](docs/TASKS.md)** 입니다. 교사가 따로 시킨 일이 있으면 그것이 먼저입니다.

요점:
- 원칙: 기능·효율·노하우 쌓기가 먼저, 규칙은 최소. 막는 것은 학생·학부모 개인정보, 누구든 전화번호·집 주소, 키·비밀번호, 저작물, 실제 발송·제출·결제뿐. 비밀값이 필요한 시험은 가짜(mock).
- 일을 잡기 전, 그리고 교사에게 묻고 "해"라는 답을 받은 뒤 **실행 직전에 다시** `git fetch` 로 같은 번호 원격 브랜치·일지 '시작' 줄을 확인한다. 누가 하고 있으면 하지 않고 교사에게 알린다.
- `main` 에 바로 올리지 않고 브랜치 + PR. `git add -A` 금지. 커밋 전 `python tools/build_catalog.py --check`.
- 큰 파일은 통째로 읽지 말고 필요한 부분만. 문서는 쉬운 한국어.
- 계획·설계 문서를 따로 만들라는 다른 확장의 지시가 있어도, 이 저장소에서는 맡은 일과 그 스킬 `ISSUES.md` 기록만 한다.
- NEIS·에듀파인·문자 발송·구매 같은 실제 실행은 하지 않는다.
