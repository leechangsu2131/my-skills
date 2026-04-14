---
name: teacher-guide-subunit-splitter
description: "초등 교사용 지도서 PDF를 차례/목차, 단원·제재 개관 페이지, 지도 계획 표, 차시 계획 텍스트 등 여러 구조 신호를 바탕으로 단원 또는 더 세부 항목 단위로 분할 저장합니다. 교과별 표현 차이가 있어도 범용적으로 분할 기준을 찾거나 시작 페이지 제목으로 그룹명을 보정해야 할 때 사용합니다."
---

# 지도서 분할기

## When to Use This Skill
- 초등 교사용 지도서 PDF를 단원 수준 또는 차시/세부 제재 수준으로 나눠야 하고,
- 문서 안에 `차례`, `목차`, `단원 개관`, `제재 개관`, `단원의 지도 계획`, `차시별 지도 계획` 같은 구조 신호가 하나 이상 있습니다.

이 Skill은 차례/목차, 개관 페이지, 지도 계획 표, 차시 계획 텍스트를 순차적으로 탐색해 가장 그럴듯한 분할 기준을 고르고, 제목이 깨지거나 잘린 경우에는 해당 시작 페이지의 제목으로 그룹명을 보정합니다.

## Quick Start
1) 먼저 필요한 패키지 설치
```bash
pip install pdfplumber pypdf
```

2) 분할 계획만 확인(권장)
```bash
python scripts/split_subunits_from_plan_table.py --pdf "지도서.pdf" --out-dir "output" --dry-run
```

3) 실제로 PDF 저장
```bash
python scripts/split_subunits_from_plan_table.py --pdf "지도서.pdf" --out-dir "output" --save
```

## 주요 옵션
- `--scan-pages N`: 문서 앞쪽에서 차례/목차, 개관, 지도 계획 후보 페이지를 찾는 범위
- `--page-offset N`: 인쇄 쪽수와 PDF 페이지가 어긋날 때 더하는 오프셋(기본 0)
- `--z-col K`: 지도서/쪽수 열 인덱스(0-based)를 강제로 지정(자동 추정이 틀릴 때)
- `--split-level detail`: 차시/세부 제재까지 더 촘촘하게 분할

## Output
- `output/<원본PDF이름>/groups.json`: 감지된 섹션, 그룹, 전략, 페이지 범위
- `output/<원본PDF이름>/pdf_splits/`: 분할된 PDF 묶음

