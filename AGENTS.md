# AGENTS.md — AI 작업자 공용 규칙 (Codex·bizcoder 등 AGENTS.md 를 읽는 도구용)

이 저장소에서 일하는 모든 AI 작업자는 **[docs/WORKER_GUIDE.md](docs/WORKER_GUIDE.md)** 를 먼저 읽고 따릅니다.
각 AI 의 지침 칸에 넣는 글은 [docs/WORKER_INSTRUCTIONS.md](docs/WORKER_INSTRUCTIONS.md). 할 일 목록은 **[docs/TASKS.md](docs/TASKS.md)**, 기본 규칙 원본은 [CONTRIBUTING.md](CONTRIBUTING.md)·[CLAUDE.md](CLAUDE.md) 입니다.

요점:
- 원칙: 기능·효율·노하우 쌓기가 먼저, 규칙은 최소. 막는 것은 학생·학부모 개인정보, 누구든 연락처(전화·이메일·주소), 키·비밀번호, 저작물(지도서 PDF), 실제 발송·제출·결제뿐.
- `main` 에 바로 올리지 않고 브랜치 + PR. `git add -A` 금지. 커밋 전 `python tools/build_catalog.py --check`.
- 스킬 하나를 고칠 때는 그 폴더의 `SKILL.md`·`ISSUES.md` 부터. 문서는 쉬운 한국어.
- NEIS·에듀파인·문자 발송·구매 같은 실제 실행은 하지 않는다.
