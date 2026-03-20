---
name: teacher-guide-subunit-splitter
description: "초등 교사용 지도서 PDF에서 '단원의 지도 계획' 표(좌측 큰 항목/열 '지' 범위) 기준으로 소단원(큰 항목)별 페이지 구간을 자동 계산해 별도 PDF로 분할 저장합니다."
---

# 지도서 소단원 분할기 (단원의 지도 계획 표 기준)

## When to Use This Skill
- 초등 교사용 지도서 PDF 안에 `단원의 지도 계획`(또는 유사 표현) 페이지가 있고,
- 그 페이지에 표가 있으며 오른쪽(또는 열 이름/표 안에서) `지` 페이지 범위(예: `6-11`, `16-23`)가 있습니다.

이 Skill은 표에서 좌측 큰 항목(소단원 그룹)별로 `지` 범위를 읽고, 그 최소/최대 범위를 합쳐 소단원별 PDF를 저장합니다.

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
- `--scan-pages N`: 문서 앞쪽에서 `단원의 지도 계획` 후보 페이지를 찾는 범위
- `--page-offset N`: 표의 `지` 숫자를 PDF 페이지로 변환할 때 더하는 오프셋(기본 0)
- `--z-col K`: 표에서 `지` 열 인덱스(0-based)를 강제로 지정(자동 추정이 틀릴 때)

## Output
- `output/<원본PDF이름>/groups.json`: 소단원(큰 항목)별 계산된 `start_page/end_page`
- `output/<원본PDF이름>/pdf_splits/`: 소단원별 분할 PDF

