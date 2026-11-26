# personal-obsidansystem-main 이슈 로그

> 이 스킬에서 생긴 문제와 해결 과정, 진행 중인 일, 할 일을 기록한다.
> 새 항목은 해당 절의 맨 위에 추가하고, 해결되면 '🟢 해결됨'으로 옮긴다. 양식은 맨 아래 주석 참고.

## 🔵 진행 중

_없음_

## 📌 백로그

### ISSUE-005: 쉼표가 든 한 줄 값(제목 등)이 목록으로 읽힘 (2026-11-26)
- **상태**: 📌 백로그 (확인 필요 — 의도한 동작일 수 있음)
- **증상**: `title: "a, b"` 를 읽으면 `["a", "b"]` (값을 `[...]` 없이 적은 경우).
- **원인**: `read_frontmatter` 가 숫자로 시작하지 않는 쉼표 글을 목록으로 나눔.
- **해결/조치**: 미정(T65 범위 밖).
- **관련 파일**: `pkm_core.py`(`read_frontmatter`)

## 🟢 해결됨

### ISSUE-004: 폴더 이름이 'Vault ' 로 시작하면 첫 폴더가 경로에서 사라짐 (2026-11-25)
- **상태**: 🟢 해결 (2026-11-26)
- **증상**: 노트의 `path` 속성이 `Vault Notes / x` 이면 `x` 폴더로 읽힘(`Vault Notes` 가 빠짐). `Vault Notes / x / y` 는 `x/y`. 그대로 `move_note_to_path_prop` 에 쓰이면 노트가 엉뚱한 폴더로 옮겨질 수 있음
- **원인**: `parse_note_folder_path_value` 가 `Vault ` 로 시작하고 `/` 가 있는 글을 '볼트 루트 / …' 표시로 보고 첫 마디를 무조건 버림. 실제 폴더 이름이 `Vault ` 로 시작하는 볼트가 있는지는 확인 필요(추정: 드묾)
- **해결/조치**: 'Vault 루트' 같은 정해진 표시만 볼트 루트로 봄. `Vault Notes` 는 실제 폴더 이름으로 읽음.
- **관련 파일**: `pkm_core.py`(`parse_note_folder_path_value`), `tests/test_pkm_core.py`

### ISSUE-003: 값에 큰따옴표가 있으면 속성을 고칠 때마다 역슬래시가 늘어남 (2026-11-25)
- **상태**: 🟢 해결 (2026-11-26)
- **증상**: 제목처럼 `say "hi"` 가 든 노트에서 다른 속성(예: domain)을 한 번 고칠 때마다 제목의 `\` 가 불어남(한 번 쓰면 `\"`, 이어서 `\\"`, …). 한 번만 써도 다시 읽으면 `say \"hi\"` 로 읽힘
- **원인**: `format_yaml_value` 는 `"` 를 `\"` 로 바꿔 쓰지만, 읽는 쪽 `parse_yaml_value` 는 따옴표만 벗기고 `\"` 를 되돌리지 않음. 그래서 읽은 값에 역슬래시가 남은 채 다시 쓰면서 계속 겹침
- **해결/조치**: 큰따옴표 값을 읽을 때 `\"`·`\\` 를 되돌리고, 쓸 때 둘 다 이스케이프. **이미 쌓인 역슬래시는 자동으로 지워지지 않음**(더 늘지는 않음).
- **관련 파일**: `pkm_core.py`(`format_yaml_value`, `parse_yaml_value`, `read_frontmatter`, `write_frontmatter`), `tests/test_pkm_core.py`

### ISSUE-002: 목록 속성의 항목에 쉼표가 있으면 여러 항목으로 쪼개짐 (2026-11-25)
- **상태**: 🟢 해결 (2026-11-26)
- **증상**: `topic: ["a, b", "c"]` 를 쓰고 다시 읽으면 `["a", "b", "c"]` 가 됨(항목이 3개로 바뀜). 속성을 한 번 고치면 그대로 파일에 저장됨
- **원인**: `format_yaml_value` 가 목록 항목을 따옴표 없이 `[a, b, c]` 로 이어 쓰고, 읽는 쪽이 쉼표로 나눔
- **해결/조치**: 쉼표·큰따옴표가 든 목록 항목은 따옴표로 감싸 쓰고, 읽을 때 따옴표 안의 쉼표는 나누지 않음.
- **관련 파일**: `pkm_core.py`(`format_yaml_value`, `parse_yaml_value`, `read_frontmatter`), `tests/test_pkm_core.py`

### ISSUE-001: 저장소 밖 obsidansystem 파이프라인을 스킬로 이관 (2026-11-20)
- **상태**: 🟢 해결 (2026-11-20)
- **증상**: 볼트 묶음·NotebookLM 분석·추천표 반영 도구가 `GitHub\obsidansystem`(별도 저장소)에만 있었고, 스킬 폴더의 `pkm_*.py`는 그보다 오래된 판이었다.
- **원인**: 스킬 보관소 정리(2026-11-18) 때 GUI 부분만 옮겨 왔다.
- **해결/조치**: `orchestrator.py`, `md_merger.py`, `notebooklm_*.py`, `apply_gemini_recommendations.py`, `pkm_batch_apply.py`, `rehome_notes_by_path.py`와 최신 `pkm_*.py`를 복사했다. 하드코딩 경로·볼트 이름을 없애고(볼트 이름은 폴더 이름에서, 경로는 중앙 `.env`의 `PERSONAL_OBSIDANSYSTEM_MAIN__VAULT`), 묶음·상태 파일은 `data_dir()`로 옮겼다. 기존 `.pkm_batch_state.json`도 `data_dir()`로 복사했다. 노트 내용이 든 `response*`, `spec_*.yaml`, `dist/`, 일회성 `make_spec_*.py`, `fix_links.py`, 외부 `mindvault-master`는 옮기지 않았다(원래 폴더에 남아 있음).
- **관련 파일**: 위 스크립트, `docs/`, `SKILL.md`

<!--
항목 양식 (복사해서 사용)

### ISSUE-001: 한 줄 제목 (YYYY-MM-DD)
- **상태**: 🔵 진행 중 | 📌 백로그 | 🟢 해결 (YYYY-MM-DD)
- **증상**: 무엇이 어떻게 안 됐나 (오류 메시지 그대로)
- **원인**: 확인된 원인
- **해결/조치**: 무엇을 바꿨나, 재발 방지
- **관련 파일**: `script.py`, 커밋 해시
-->
