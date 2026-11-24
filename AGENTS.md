# AGENTS.md — AI 작업자 공용 규칙 (Codex·bizcoder 등 AGENTS.md 를 읽는 도구용)

이 저장소에서 일하는 모든 AI 작업자는 **[docs/WORKER_GUIDE.md](docs/WORKER_GUIDE.md)** 를 먼저 읽고 따릅니다.
할 일 목록은 **[docs/TASKS.md](docs/TASKS.md)**, 기본 규칙 원본은 [CONTRIBUTING.md](CONTRIBUTING.md)·[CLAUDE.md](CLAUDE.md) 입니다.

요점:
- 학생·교사 이름, 전화번호, 키·비밀번호, 절대 경로를 코드·문서·커밋에 쓰지 않는다.
- `main` 에 바로 올리지 않고 브랜치 + PR. `git add -A` 금지. 커밋 전 `python tools/build_catalog.py --check`.
- 스킬 하나를 고칠 때는 그 폴더의 `SKILL.md`·`ISSUES.md` 부터. 문서는 쉬운 한국어.
- NEIS·에듀파인·문자 발송·구매 같은 실제 실행은 하지 않는다.
