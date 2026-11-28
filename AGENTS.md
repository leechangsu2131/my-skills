# AGENTS.md — AI 작업자 공용 규칙 (Codex·Antigravity·bizcoder 등 AGENTS.md 를 읽는 도구용)

이 저장소에서 일하는 모든 AI 작업자는 **[docs/WORKER_GUIDE.md](docs/WORKER_GUIDE.md)** 를 먼저 읽고 따릅니다.
각 AI 의 지침 칸에 넣는 글은 [docs/WORKER_INSTRUCTIONS.md](docs/WORKER_INSTRUCTIONS.md). 할 일 목록은 **[docs/TASKS.md](docs/TASKS.md)**, 기본 규칙 원본은 [CONTRIBUTING.md](CONTRIBUTING.md)·[CLAUDE.md](CLAUDE.md) 입니다.

요점:
- **수업 비서가 먼저**(docs/TASKS.md 맨 위 ★). TASKS 에 고를 일이 없으면 `claim_task.py --next` 가 열린 이슈가 있는 다른 스킬 하나(S8)를 준다 — 잡은 스킬만 고치고, 그 밖에서 본 문제는 그 스킬 `ISSUES.md` 에 한 줄(교사 결정 2026-11-28).
- 원칙: 기능·효율·노하우 쌓기가 먼저, 규칙은 최소. 막는 것은 학생·학부모 개인정보(단, 교사가 요청한 본인 개인 Google Drive·시트 업로드는 허용, Git 저장소 커밋은 금지), 누구든 전화번호·집 주소(저장소·공개 공간), 키·비밀번호, 저작물(지도서 PDF), 교사 확인 없는 실제 발송·제출·결제뿐(비서 일은 아래 마지막 줄).
- 일을 잡기 전, 그리고 교사에게 묻고 "해"라는 답을 받은 뒤 **실행 직전에 다시** `python tools/claim_task.py <번호> <짧은-영어> --name <내 이름>` 으로 확인하며 잡는다(❌ 면 하지 않고 교사에게 알림). 교사 PC 의 로컬 IDE(Codex·Antigravity)는 원래 `my-skills` 폴더에서 한 번에 하나만, 시작·중간·끝에 `python tools/sync_work.py start <브랜치>` / `save` / `end`(받기·main 합치기·올리기). 까만 창 CLI 작업자는 `tools/start_worker.ps1` 이 만든 `my-skills-<이름>` 폴더에서만 일한다. 푸시가 안 되는 곳(인터넷이 막힌 웹 Codex 등)이면 교사가 준 '이번 일'만 한다(교사 PC 가 미리 잡아 둠).
- `main` 에 바로 올리지 않고 브랜치 + PR. `git add -A` 금지. 커밋 전 `python tools/build_catalog.py --check`.
- 스킬 하나를 고칠 때는 그 폴더의 `SKILL.md`·`ISSUES.md` 부터. 문서는 쉬운 한국어.
- **실제 실행**(NEIS·에듀파인 신청·상신·제출, 문자·메신저 발송, 구매·결제, 삭제): 작업자로 맡은 일(TASKS·브랜치·코드 고치기)에서는 하지 않는다(시험은 DRY_RUN·가짜). **교사 PC 에서 교사가 대화로 직접 시킨 비서 일**(예: "오늘 조퇴 상신해줘", "이 공문 처리해줘")은 **한다** — 그 스킬 `SKILL.md` 대로 끝까지 진행하고, 빠진 정보(시간·사유 등)는 묻고, 화면을 다 채운 뒤 되돌릴 수 없는 마지막 단추(승인요청·상신·발송·결제) **바로 전에만** 내용을 보여 주고 "누를까요?" 한 번 확인받아 누른다. 비서 일은 저장소를 고치지 않으므로 브랜치·`claim_task.py`·`sync_work.py` 가 필요 없다(교사 결정 2026-11-27).
