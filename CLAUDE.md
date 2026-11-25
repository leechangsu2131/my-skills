# my-skills — Claude 작업 지침

여러 사람이 함께 쓰는 스킬 보관소다. 아래 두 문서가 기본 규칙이며 Claude Code도 그대로 따른다.

@README.md
@CONTRIBUTING.md

## Claude 작업 시 덧붙이는 규칙
- `CONTRIBUTING.md`의 도구별 역할 표(Antigravity·Cursor·Codex)는 참고용이다. Claude Code는 기획·구현·검토를 모두 맡을 수 있다.
- **(임시, 2026-11-20~) 교사 PC 의 Claude Code 는 `main`에 바로 커밋·푸시한다.** 브랜치·PR은 만들지 않는다. **Claude Code 웹 등 다른 곳에서 작업자로 일하는 Claude 는 해당하지 않는다** — `docs/WORKER_GUIDE.md` 대로 `task/…` 브랜치 + PR. 나중에 PR 방식으로 돌아갈 예정이다(`CONTRIBUTING.md` "커밋·푸시 방식" 참고).
  - 커밋 전 `git diff --staged`로 **학생·학부모 개인정보, 누구든 전화번호·집 주소, 비밀값**이 없는지 확인한다(공개 저장소). 교사·교직원·작업자 이름, 이메일 주소, 학교 업무 정보는 막지 않는다 — 원칙은 기능·효율·노하우 쌓기, 규칙은 법적·금전적 위험이나 실제 피해가 있는 것만(교사 결정 2026-11-25).
  - 내가 고친 파일만 골라 `git add <파일>` 한다. 다른 세션·도구가 고치는 중인 파일은 함께 올리지 않는다(`git add -A` 금지).
  - 푸시 전 `git pull --rebase`로 원격 변경을 먼저 받는다. 다른 세션의 미커밋 파일 때문에 막히면 `git fetch` 후 뒤처졌을 때만 `--autostash`를 붙인다.
- 스킬 하나를 고칠 때는 그 폴더의 `SKILL.md`와 `ISSUES.md`부터 읽는다. 다른 스킬 폴더는 필요할 때만 연다.
- `CATALOG.md`는 직접 고치지 않는다. 메타데이터를 고친 뒤 `python tools/build_catalog.py`, 마무리 전 `python tools/build_catalog.py --check`.
- 비밀값은 중앙 `.env`, 결과물·개인정보는 `data_dir()` — 코드·문서·커밋 메시지에 비밀값·학생 정보·전화번호를 쓰지 않는다.
- **다른 AI 작업자 관리(오케스트레이션)**: 작업자 브랜치·PR 검토·합치기, `docs/TASKS.md` 상태 정리, 빈 작업자에게 줄 프롬프트 만들기는 `docs/ORCHESTRATION.md` 절차대로 한다(집·학교 PC 공통). 검토 에이전트는 저장소의 `.claude/agents/reviewer.md`. 작업자 규칙은 `docs/WORKER_GUIDE.md`. Claude Code 는 `my-skills` 폴더에서 연다. 교사가 "현황", "작업자들 어때"라고 하면 `python tools/work_status.py --fetch --md` 로 시작하는 `docs/ORCHESTRATION.md` 0-1 순서를 돈다.
- NEIS·에듀파인·메신저 발송·구매처럼 **실제로 바깥에 영향을 주는 실행**(제출, 발송, 결제, 삭제)은 사용자에게 먼저 묻는다. 시험은 `DRY_RUN` 류 설정이 있으면 그것부터 쓴다.
