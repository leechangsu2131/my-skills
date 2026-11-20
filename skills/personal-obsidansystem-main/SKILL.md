---
name: personal-obsidansystem-main
description: Google Drive 안의 Obsidian 볼트(개인 PKM 메모)를 운용지침에 맞게 저장·분류·정리할 때 쓴다. 인박스·루트에 쌓인 메모 분류, 노트 속성(domain·engine·topic·type) 일괄 수정, 볼트를 묶음(md)으로 만들어 NotebookLM·Gemini에 올리기, Gemini·NotebookLM 추천표를 볼트에 반영, NotebookLM 소스를 md로 받아 볼트에 넣기. '옵시디언', '볼트', '메모 정리', '인박스 정리', 'PKM', '노트북LM 묶음', '병합본' 같은 말이 나오면 쓴다.
metadata:
  category: 개인·생활
  status: 운영
  version: v0.2.0
  summary: Obsidian 볼트 메모를 운용지침에 맞게 분류·정리한다. 속성 일괄 수정 GUI, 볼트 묶음(md) 생성 → NotebookLM/Gemini 분석 → 추천표 검증·반영 파이프라인, NotebookLM 소스 추출 연계를 담았다.
---

# personal-obsidansystem-main

Google Drive에 있는 Obsidian 볼트를 볼트 안 운용지침(`PKM_Rules/PKM_운용지침_v*.md`)에 맞게 정리하는 도구 모음이다.
예전에는 저장소 밖 `GitHub\obsidansystem` 폴더에 따로 있던 파이프라인을 2026-11-20에 이 스킬로 옮겨 왔다.

## 언제 쓰나
- 인박스(`00_Inbox`)나 볼트 맨 위에 흩어진 메모를 분류·이동하고 속성을 달 때
- 볼트 전체를 NotebookLM·Gemini에 올려 분석시키고, 받은 추천표를 볼트에 반영할 때
- 노트 속성(frontmatter)을 한 화면에서 확인·일괄 수정할 때
- NotebookLM에서 모은 자료(유튜브·웹 소스)를 md로 받아 볼트에 넣을 때

## 역할 나누기 (중요)
| 일 | 누가 | 이유 |
|---|---|---|
| 새 메모 분류·이동(인박스, 루트 노트 수십 개) | **Claude가 직접** | 새 메모 몇 개와 운용지침만 읽으면 된다. 표로 제안 → 사용자 승인 → 반영 |
| 볼트 전체 질문·노트 사이 연결 찾기 | **NotebookLM** | 수백 개 노트를 통째로 이해하는 일은 NotebookLM이 잘한다. Claude가 볼트 전체를 읽지 않는다 |
| 수백 개 재분류 | 파이프라인(아래) + NotebookLM/Gemini | 대량 작업 |
| "그 메모 어디 있지?" | Claude (낱말 검색) | 전체를 읽을 필요 없음 |

## Claude 행동 지침
- 볼트 경로는 중앙 `.env`의 `PERSONAL_OBSIDANSYSTEM_MAIN__VAULT`에 있다. 코드·문서·커밋에 실제 경로를 쓰지 않는다(공개 저장소, 경로에 사용자 이름이 들어 있다).
- 분류 전에 볼트의 `PKM_Rules/PKM_운용지침_v*.md`에서 **필요한 절만** 찾아 읽는다(속성 스키마, Domain 판별, 폴더 구조, 노트 제목 원칙, 00_INBOX 처리 원칙). 지침 전체나 볼트 전체를 통째로 읽지 않는다.
- 인박스 정리 순서: ① 대상 메모 목록 → ② `파일 | 제안 제목 | domain | engine | topic | type | 옮길 폴더 | 이유` 표로 제안 → ③ **사용자 승인 후에만** 이동·속성 기록. 승인 없이 파일을 옮기거나 지우지 않는다.
- 파일을 옮길 때는 링크가 깨지지 않게 `pkm_core.update_links_for_note_change`를 쓰거나 Obsidian CLI `move`를 쓴다(그냥 파일 이동 금지).
- 볼트에는 git이 없다(구글 드라이브 버전 기록으로 대신). 일괄 수정 전에는 도구의 자동 백업(`<내 문서>\backupvault`)이 켜져 있는지 확인하고, 먼저 `--dry-run`으로 돌린다.
- 결과물(묶음, 응답, CSV, 상태 파일)에는 노트 내용이 들어 있으므로 `data_dir()`(`<내 문서>\my-skills-data\personal-obsidansystem-main\`)에만 둔다.

## 준비
- Python 3.10+, `pip install pyyaml` (나머지는 표준 라이브러리)
- 중앙 `.env`: `PERSONAL_OBSIDANSYSTEM_MAIN__VAULT=<볼트 경로>` (`.env.example` 참고)
- (선택) Obsidian CLI — `apply_gemini_recommendations.py`가 이동·속성 기록에 쓴다

## 사용법
```powershell
# 속성 일괄 확인·수정 GUI
python pkm_manager.py

# 대량 정리 파이프라인 (NotebookLM/Gemini 왕복)
python orchestrator.py merge "<볼트 경로>" --target 45      # 1. 묶음(md) 생성 → data_dir\notebooklm_bundle
python orchestrator.py batch-prompt "<볼트 경로>" --copy    # 2. 30개 단위 분석 프롬프트 (클립보드)
python orchestrator.py parse <응답.md>                       # 3. 응답 표 검증 → CSV
python apply_gemini_recommendations.py "<볼트 경로>" <추천.csv> --dry-run   # 4. 미리보기 후 반영

# YAML 지시서로 배치 적용 (병합·새 노트 생성 포함)
python pkm_batch_apply.py <spec.yaml> --dry-run
```

## 문서
- [docs/파이프라인_사용법.md](docs/파이프라인_사용법.md) — 묶음 → NotebookLM → 파싱 → 반영 전체 흐름
- [docs/Gemini_추천표_적용.md](docs/Gemini_추천표_적용.md) — 추천표 열 구성, 처리 제안별 동작
- [docs/YAML_배치_적용.md](docs/YAML_배치_적용.md) — `pkm_batch_apply.py` 지시서 형식
- [docs/경로_재배치.md](docs/경로_재배치.md) — `rehome_notes_by_path.py`
- [docs/NotebookLM_소스_추출.md](docs/NotebookLM_소스_추출.md) — 북마클릿으로 NotebookLM 소스를 md로 받아 볼트·Claude에 쓰기
- [PKM_도구_사용설명서.md](PKM_도구_사용설명서.md) — 속성 관리 GUI
- [ISSUES.md](ISSUES.md) — 문제·해결 기록, 진행 중인 일
