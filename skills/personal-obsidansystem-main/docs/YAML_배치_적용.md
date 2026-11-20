# PKM Batch Apply Tool

## 개요

`pkm_batch_apply.py`는 NotebookLM이나 AI가 생성한 노트 재구성 명세(YAML)를 받아서,
옵시디언 볼트 내 노트들의 **frontmatter 업데이트 + 폴더 이동**을 자동으로 처리하는 재사용 가능한 도구입니다.

### 핵심 원칙
- **파일명(제목) 절대 변경 안 함** — 이동만 처리
- **해시 기반 사용자 수정 감지** — 시간이 아닌 내용의 변화로 판단
- **dry-run 우선** — 항상 `--dry-run`으로 미리보기 후 실제 적용
- **링크 자동 업데이트** — obsidian CLI `move` 명령 우선 사용, 없으면 `pkm_core` fallback

---

## 사용법

```powershell
# 미리보기 (실제 변경 없음)
python -X utf8 pkm_batch_apply.py spec_파일명.yaml --dry-run

# 실제 적용
python -X utf8 pkm_batch_apply.py spec_파일명.yaml
```

> **Windows에서는 반드시 `-X utf8` 플래그를 붙이세요** (한글+이모지 출력을 위해)

---

## YAML 명세 파일 작성법

```yaml
vault: "<볼트 경로>"   # 볼트 경로 (슬래시 사용)

notes:
  - stem: "과거인정"                  # 파일명(확장자 제외), 필수
    target_folder: "30_SYSTEM/자기"   # 이동할 폴더, 생략 시 현재 위치 유지
    frontmatter:                      # 업데이트할 속성만 기재 (생략 가능)
      domain: 자기
      engine: principle
      topic: [과거수용, 감정조절]

  # 예시 2: 본문 전체 덮어쓰기 (기존 방식)
  - stem: "과거인정"
    body: |                           # 본문 전체. 생략 시 기존 본문 유지
      판단능력은 항상 키워가되...

  # 예시 3: 본문은 유지하고 텍스트나 링크만 하단에 추가하기 (새로운 방식)
  - stem: "과거인정"
    append_body: |
      추가하고 싶은 텍스트 내용...
    append_links: ["선택과 후회에 대한 자기 성찰", "다른 링크"]
```

### stem 기준 파일 탐색

도구는 `{stem}.md` 파일을 볼트 전체에서 검색합니다. 사용자가 파일을 **다른 폴더로 이미 옮겼어도** 자동으로 찾아냅니다.

- ✅ 찾음: frontmatter 업데이트 + target_folder로 이동
- ✅ 이미 target_folder에 있음: 내용만 업데이트 (이동 생략)
- ❌ 못 찾음: target_folder에 새로 생성
- ⚠️ `--skip-recent N`으로 N시간 내 수정본은 건너뜀

---

## 사용자 수정 감지 방식 (해시 기반)

배치를 적용할 때마다 각 노트 내용의 **SHA-1 해시**를 `.pkm_batch_state.json`에 저장합니다.

```
obsidansystem/
└── .pkm_batch_state.json   ← "내가 마지막으로 쓴 내용의 지문"
```

다음에 같은 노트를 다시 배치 적용하려 할 때:

| 비교 결과 | 의미 | 처리 |
|-----------|------|------|
| `hash(현재 파일)` **==** `저장된 hash` | 사용자가 건드리지 않음 | 안전하게 덮어씀 |
| `hash(현재 파일)` **≠** `저장된 hash` | 사용자가 직접 수정함 | `SKIPPED_USER_EDIT` 건너뜀 |
| 저장된 hash 없음 (첫 실행) | 이전 배치 기록 없음 | 그냥 적용 |

> **강제 덮어쓰기**: `.pkm_batch_state.json`에서 해당 stem 항목을 삭제하면 다음 실행 시 강제 적용됩니다.

---

## 상태 코드 설명

| 상태 | 의미 |
|------|------|
| `MOVED_CLI` | obsidian CLI로 이동 (링크 자동 업데이트됨) |
| `MOVED_PY` | Python fallback으로 이동 (pkm_core 링크 업데이트) |
| `UPDATED` | 같은 폴더에서 내용만 업데이트 |
| `CREATED` | 새로 생성 |
| `SKIPPED` | 변경 사항 없음 |
| `SKIPPED_USER_EDIT` | 사용자가 직접 수정한 파일 → 건너뜀 |
| `NOT_FOUND` | 볼트에서 못 찾고 target_folder도 없음 |

---

## 폴더 구조 권장

```
obsidansystem/
├── pkm_batch_apply.py      ← 이 도구
├── pkm_core.py             ← 의존 라이브러리
├── spec_자기성찰성장.yaml  ← 이번 배치 명세
├── spec_인간관계.yaml      ← 다음 배치 명세 (예시)
└── spec_투자.yaml          ← ...
```

---

## obsidian CLI 연동

obsidian CLI가 설치되어 있고 옵시디언이 실행 중이면,
`move` 명령으로 파일을 이동할 때 **옵시디언이 직접 내부 링크를 업데이트**합니다.

설치 방법: 옵시디언 앱 → 설정 → 일반 → **명령줄 인터페이스 활성화**

CLI 없이도 `pkm_core.update_links_for_note_change()`로 Python 수준에서 링크를 업데이트하므로
CLI 미설치 시에도 정상 작동합니다.
