"""NotebookLM prompt templates for PKM analysis.

Based on PKM_운용지침_v14 specification.
Three analysis tiers:
  1. full   — 속성 + 제목 + 연결 후보 + 처리 제안 (12열)
  2. title  — 제목 개선만 (6열)
  3. links  — 연결 후보만 (8열)
"""

from __future__ import annotations

# ── v14 허용값 ────────────────────────────────────
DOMAIN_VALUES = ("수업", "학급", "투자", "자기", "관계", "DIY", "생산성", "횡단")

ENGINE_VALUES = ("concept", "pattern", "principle", "experiment")

TYPE_VALUES = ("감상문", "수업안", "거시예측", "시장일지", "자서전", "리소스")

ACTION_VALUES = (
    "유지",
    "제목 수정 후 유지",
    "기존 노트에 흡수",
    "10_NOTE 승격",
    "20_THINKING 승격",
    "30_SYSTEM 승격",
    "Inbox 보류",
)

CONFIDENCE_VALUES = ("상", "중", "하")

# ── 프리앰블: 모든 프롬프트 앞에 붙는 공통 규칙 ──────────
_PREAMBLE = """\
너는 사용자의 PKM 보조 분석가다.
반드시 PKM_운용지침_v14를 정본 기준으로 따른다.

중요:
너에게 제공되는 파일은 원본 Vault 파일이 아니라, NotebookLM 업로드용으로 병합된 번들 파일이다.

따라서:
- 번들 파일명은 실제 노트명이 아니다.
- 번들 파일명으로 제목 수정이나 YAML 판단을 하지 마라.
- 반드시 각 섹션 제목과 `원본 파일:` 줄을 기준으로 원본 노트를 식별하라.
- 분석 단위는 파일이 아니라 섹션이다.
- `source_path`를 확인할 수 없는 항목은 보류하라.
- 실제 반영 기준 키는 `bundle_file`이 아니라 `source_path`다.
"""

# ── 공통 속성 규칙 ─────────────────────────────────
_SCHEMA_RULES = """\
반드시 지킬 규칙:
- domain은 v14 허용값만 사용한다: 수업 / 학급 / 투자 / 자기 / 관계 / DIY / 생산성 / 횡단
- engine은 concept / pattern / principle / experiment 만 사용한다.
- type은 감상문 / 수업안 / 거시예측 / 시장일지 / 자서전 / 리소스 안에서만 사용한다.
- topic은 구체적 대상어만 쓴다.
- topic은 반드시 `[a]` 또는 `[a, b]` 형식으로 쓴다.
- domain 이름이나 engine 이름을 topic으로 쓰지 않는다.
- type이 불필요하면 빈칸으로 둔다.
- `제안 제목`은 새로운 제목을 제안하지 말고 무조건 `(유지)`라고만 적는다. 제목은 절대 바꾸면 안 된다.
- `source_path`는 `원본 파일:` 줄의 값을 축약 없이 그대로 복사한다.
- `...` 같은 생략 기호를 source_path에 쓰지 않는다.
- `bundle_file`은 참고용이다. 실제 판단 기준은 source_path다.
- 확신이 낮으면 억지로 채우지 말고 보류하라.
"""

# ── 본문 작성 및 병합(Rewrite & Merge) 규칙 ──────────
_CONTENT_RULES = """\
본문 내용 정리 및 병합(Merge) 지시를 받을 시 다음 원칙을 엄격하게 지켜야 한다:
1. 디테일 보존: 선생님의 고유한 감정선, 날짜별 기록, 첨부된 유튜브 링크 및 참고 자료는 아예 삭제하지 않고 반드시 포함한다.
2. 밀도 있는 요약: 불필요하게 반복되거나 장황한 서술은 문맥과 핵심 주장이 훼손되지 않는 선에서 깔끔하게 요약하여 읽기 좋게 만든다.
3. 안전한 병합: 여러 단상들을 하나로 합칠 때, 개별 메모가 가졌던 '원래의 문제의식'이 통째로 누락되는 일이 없도록 각별히 점검한다.
"""

# ── 처리 제안 ↔ engine 일관성 규칙 ──────────────────
_CONSISTENCY_RULES = """\
- 처리 제안은 다음 중 하나만 사용한다:
  유지 / 제목 수정 후 유지 / 기존 노트에 흡수 / 10_NOTE 승격 / 20_THINKING 승격 / 30_SYSTEM 승격 / Inbox 보류
- 처리 제안과 engine은 서로 모순되면 안 된다.
  - `20_THINKING 승격`이면 engine은 원칙적으로 `pattern`
  - `30_SYSTEM 승격`이면 engine은 원칙적으로 `principle`
  - `10_NOTE 승격`이면 engine은 원칙적으로 `concept` 또는 `experiment`
- `type=리소스`는 참고자료 성격일 때만 쓴다.
  - 원칙, 실험, 성찰이 분명한 노트에는 `리소스`를 붙이지 않는다.

연결 후보 탐색 지침 (매우 중요):
- 제공된 전체 문서를 바탕으로, 이 노트와 개념적으로 이어지거나 함께 보면 좋을 다른 원본 노트를 '연결 후보' 열에 적극적으로 제안하라.
- 연결 후보는 반드시 **변경되기 전의 원본 파일명(또는 기존 제목)** 형태(예: `기존개념.md`)여야 한다. 새롭게 지어낸 제안 제목을 넣으면 링크가 깨지므로 절대 안 된다.
- 예: A 노트가 '투자 가중치'를 다루고 B 노트가 '의사결정 프로세스'를 다루면 서로 연결 후보로 제안한다.
- 다른 파일의 내용과 중복되거나 유사하면 '기존 노트에 흡수' 처리 제안을 내리고, 흡수 대상 노트를 연결 후보에 적는다.
"""

# ── 출력 규칙 ──────────────────────────────────────
_OUTPUT_RULES = """\
- 출력은 반드시 표로만 한다.
- 표 뒤에 해설이나 설명을 추가하지 않는다.
- `source_path`가 없는 행은 출력하지 않는다.
"""

# ── YAML 출력 규칙 ───────────────────────────────────
_OUTPUT_RULES_YAML = """\
- 출력은 반드시 아래와 같은 YAML 형식 코드 블록으로만 한다.
- 기존 본문을 유지하면서 밑에 텍스트만 추가하려면 `append_body:` 를 사용하고, 전체 내용을 요약/재작성해야 할 때만 `body:` 를 사용한다.
- 기존 노트와 연결할 링크들은 `append_links:` 배열에 넣는다.
- 파일명은 절대 임의로 바꾸지 말고, 원본 파일명(확장자 제외) 그대로 `stem`에 적는다.
- 분류에 따라 이동이 필요하면 `target_folder`에 "10_NOTE/도메인명" 형태로 경로를 지정한다.
- YAML 외에 불필요한 설명은 출력하지 않는다.

[출력 양식 예시]
```yaml
vault: "<볼트 경로>"

notes:
  - stem: "원본 파일명"
    target_folder: "10_NOTE/DIY"
    frontmatter:
      domain: DIY
      engine: concept
      topic: [핵심어1, 핵심어2]
    append_links: ["연결할 노트 1", "연결할 노트 2"]
    append_body: |
      추가로 덧붙일 내용이나 요약 코멘트를 여기에 작성.
```
"""

# ── 1. FULL: 속성 + 제목 + 연결 + 처리 제안 (12열) ─────

PROMPT_FULL = (
    _PREAMBLE
    + "\n이번 작업의 목표:\n"
    "- 아래 병합본 파일들 안의 각 섹션을 읽고\n"
    "- 원본 노트 단위로\n"
    "  - 제안 제목 (절대 새로 짓지 말고 무조건 '(유지)'라고 적을 것)\n"
    "  - domain / engine / topic / type 후보\n"
    "  - 연결 후보 (빈칸으로 두지 말고 본문과 관련된 다른 노트를 반드시 탐색할 것)\n"
    "  - 처리 제안\n"
    "  - 확신도\n"
    "를 제안하라.\n\n"
    + _SCHEMA_RULES
    + "\n"
    + _CONSISTENCY_RULES
    + "\n"
    + _CONTENT_RULES
    + "\n"
    + _OUTPUT_RULES
    + "\n"
    "출력 열:\n"
    "bundle_file | source_path | 현재 제목 | 제안 제목 | domain | engine | topic | type | 연결 후보 | 처리 제안 | 확신도 | 이유\n"
)

# ── 2. TITLE: 제목만 ───────────────────────────────

PROMPT_TITLE = (
    "너는 PKM 제목 편집자다.\n\n"
    "중요:\n"
    "입력 파일은 원본 노트가 아니라 병합된 번들 파일이다.\n"
    "분석 단위는 섹션이며, 각 섹션의 `원본 파일:` 줄을 기준으로 원본 노트를 식별하라.\n\n"
    "목표:\n"
    "- 원본 노트 기준으로 제목 개선안만 제안하라.\n\n"
    "규칙:\n"
    "- 번들 파일명은 제목 후보로 사용하지 않는다.\n"
    "- 기존 제목이 이미 좋으면 `(유지)`라고 쓴다.\n"
    "- 제목만 보고 내용이 짐작되어야 한다.\n"
    "- 나쁜 제목: 추상적 단어 하나 (예: 생각하는 힘)\n"
    "- 좋은 제목: 주어 + 핵심 주장 (예: 질문을 설계하면 사고가 깊어진다)\n"
    "- 너무 넓거나 모호한 제목은 피한다.\n"
    + _OUTPUT_RULES
    + "\n"
    "출력 열:\n"
    "bundle_file | source_path | 현재 제목 | 제안 제목 | 유지 가능 여부 | 이유\n"
)

# ── 3. LINKS: 연결 후보만 ──────────────────────────

PROMPT_LINKS = (
    "너는 PKM 연결 편집자다.\n\n"
    "중요:\n"
    "입력 파일은 NotebookLM 업로드용 병합본이다.\n"
    "분석 단위는 개별 섹션이며, 각 섹션의 `원본 파일:` 줄을 기준으로 원본 노트를 식별하라.\n\n"
    "목표:\n"
    "- 원본 노트별로 연결 후보를 보수적으로 제안하라.\n\n"
    "규칙:\n"
    "- 제목 유사성만으로 연결하지 않는다.\n"
    "- source_path 없는 항목은 제안하지 않는다.\n"
    "- 각 연결마다 이유를 한 줄로 적는다.\n"
    "- 흡수 후보와 단순 링크 후보를 구분한다.\n"
    + _OUTPUT_RULES
    + "\n"
    "출력 열:\n"
    "bundle_file | source_path | 현재 제목 | 연결 후보 | 연결 종류 | 이유 | 처리 제안 | 확신도\n"
)

# ── 4. YAML SPEC: YAML 명세서 출력 ──────────────────────────

PROMPT_YAML_SPEC = (
    _PREAMBLE
    + "\n이번 작업의 목표:\n"
    "- 아래 병합본 파일들 안의 각 섹션을 읽고\n"
    "- 옵시디언 볼트 정리를 위한 YAML 명세서를 작성하라.\n\n"
    + _SCHEMA_RULES
    + "\n"
    + _CONSISTENCY_RULES
    + "\n"
    + _OUTPUT_RULES_YAML
)


# ── 검증 함수: NotebookLM 응답 품질 점검 ─────────────

def validate_row(row: dict[str, str]) -> list[str]:
    """Return list of issues found in a parsed recommendation row."""
    issues: list[str] = []
    sp = row.get("source_path", "").strip()

    # 1. source_path 존재 확인
    if not sp:
        issues.append("source_path가 비어 있음")
        return issues

    # 2. source_path 축약 검사
    if "..." in sp or "(" in sp and ")" not in sp:
        issues.append(f"source_path 축약 의심: {sp}")

    # 3. domain 허용값
    domain = row.get("domain", "").strip()
    if domain and domain not in DOMAIN_VALUES:
        issues.append(f"domain 허용값 위반: {domain}")

    # 4. engine 허용값
    engine = row.get("engine", "").strip()
    if engine and engine not in ENGINE_VALUES:
        issues.append(f"engine 허용값 위반: {engine}")

    # 5. type 허용값
    note_type = row.get("type", "").strip()
    if note_type and note_type not in TYPE_VALUES:
        issues.append(f"type 허용값 위반: {note_type}")

    # 6. 처리 제안 허용값
    action = row.get("처리 제안", "").strip()
    if action and action not in ACTION_VALUES:
        issues.append(f"처리 제안 허용값 위반: {action}")

    # 7. 확신도 허용값
    confidence = row.get("확신도", "").strip()
    if confidence and confidence not in CONFIDENCE_VALUES:
        issues.append(f"확신도 허용값 위반: {confidence}")

    # 8. topic 형식 (반드시 [a] or [a, b] 형식)
    topic = row.get("topic", "").strip()
    if topic and not topic.startswith("["):
        issues.append(f"topic 형식 위반 (배열 아님): {topic}")

    # 9. topic에 상위어 사용 금지
    if topic:
        lower = topic.lower().strip("[]")
        for forbidden in DOMAIN_VALUES + ENGINE_VALUES:
            if lower == forbidden.lower():
                issues.append(f"topic에 상위어 사용: {topic}")

    # 10. 처리 제안 ↔ engine 일관성
    if action == "20_THINKING 승격" and engine and engine != "pattern":
        issues.append(f"20_THINKING 승격인데 engine={engine} (pattern이어야 함)")
    if action == "30_SYSTEM 승격" and engine and engine != "principle":
        issues.append(f"30_SYSTEM 승격인데 engine={engine} (principle이어야 함)")
    if action == "10_NOTE 승격" and engine and engine not in ("concept", "experiment"):
        issues.append(f"10_NOTE 승격인데 engine={engine}")

    # 11. principle인데 type=리소스
    if engine == "principle" and note_type == "리소스":
        issues.append("engine=principle인데 type=리소스 (모순)")

    # 12. 확신도 '하'인데 과도한 단정
    if confidence == "하" and action and action not in ("Inbox 보류", "유지"):
        issues.append(f"확신도 '하'인데 적극적 처리 제안: {action}")

    return issues


def select_prompt(tier: str) -> str:
    """Return prompt text for the given tier."""
    mapping = {
        "full": PROMPT_FULL,
        "title": PROMPT_TITLE,
        "links": PROMPT_LINKS,
        "yaml_spec": PROMPT_YAML_SPEC,
    }
    if tier not in mapping:
        raise ValueError(f"Unknown tier: {tier}. Choose from: {list(mapping)}")
    return mapping[tier]
