# 검토: task/T90-guide-gitignore (PR #96)

- 검토: claude-web-은정 · 2026-11-27 (상시 일 S2)
- 대상 커밋: `b6855e1` — main `0860dcb` 기준
- **판정: 🟢 합치기 권함**

## 확인한 것

- `output/`·`pdf_splits/`·`groups.json`·`*.pdf` 가 막힘(`git check-ignore`). 이미 추적 중인 파일 중 새로 걸리는 것 없음.

## 🟡 더 막으면 좋은 것

- `auto_split.py` 는 `--out-dir` 이 없으면 **원본 PDF 옆** `auto_split/<파일명>/` 에 지도서에서 뽑은 글(`page_heads.md`, `<단원>.md`, `analysis.json`)을 만듦. 원본을 이 스킬 폴더 안에 두면 이 글은 안 막힘(`auto_split/x/index.md` 로 확인) → `auto_split/` 추가 권장.
- 스킬 폴더 안의 `.zip` 도 안 막힘(지도서 ZIP 을 여기 두는 경우, **추정**).
