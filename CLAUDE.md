# my-skills — Claude 작업 지침

여러 사람이 함께 쓰는 스킬 보관소다. 아래 두 문서가 기본 규칙이며 Claude Code도 그대로 따른다.

@README.md
@CONTRIBUTING.md

## Claude 작업 시 덧붙이는 규칙
- `CONTRIBUTING.md`의 도구별 역할 표(Antigravity·Cursor·Codex)는 참고용이다. Claude Code는 기획·구현·검토를 모두 맡을 수 있다.
- `main`에 직접 커밋·푸시하지 않는다. 브랜치(`feature/…`, `fix/…`, `docs/…`)에서 작업하고 PR을 만든다. 머지는 사람이 한다.
- 스킬 하나를 고칠 때는 그 폴더의 `SKILL.md`와 `ISSUES.md`부터 읽는다. 다른 스킬 폴더는 필요할 때만 연다.
- `CATALOG.md`는 직접 고치지 않는다. 메타데이터를 고친 뒤 `python tools/build_catalog.py`, 마무리 전 `python tools/build_catalog.py --check`.
- 비밀값은 중앙 `.env`, 결과물·개인정보는 `data_dir()` — 코드·문서·커밋 메시지에 실제 값(이름·번호·비밀번호)을 쓰지 않는다.
- NEIS·에듀파인·메신저 발송·구매처럼 **실제로 바깥에 영향을 주는 실행**(제출, 발송, 결제, 삭제)은 사용자에게 먼저 묻는다. 시험은 `DRY_RUN` 류 설정이 있으면 그것부터 쓴다.
