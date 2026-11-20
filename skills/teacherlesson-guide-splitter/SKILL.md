---
name: teacher-guide-subunit-splitter
description: "초등 교사용 지도서 PDF를 차례/목차, 단원·제재 개관 페이지, 지도 계획 표, 차시 계획 텍스트 등 여러 구조 신호를 바탕으로 단원 또는 더 세부 항목 단위로 분할 저장합니다. 교과별 표현 차이가 있어도 범용적으로 분할 기준을 찾거나 시작 페이지 제목으로 그룹명을 보정해야 할 때 사용합니다."
metadata:
  category: 수업·교사 도구
  status: 운영
  summary: 지도서 PDF를 구조 신호에 따라 단원 또는 세부 항목으로 분할하고 그룹명을 보정한다.
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

## 분할기가 안 맞는 지도서 (2026-11 추가)

예전에는 제미나이에 쪽수를 물어 직접 나눴던 경우를 아래 두 스크립트로 대신한다.

- `scripts/split_by_lesson_headers.py` — 쪽 머리에 `12차시 3`, `2~3 9차시`, 프로젝트의 `… 4차시 1`처럼 차시 표시가 있는 지도서(아이스크림 수학 등). 단원별 PDF 여러 개를 한 번에 나누고 mapper 형식(`<폴더>/groups.json`, `pdf_splits/`)으로 저장한다. 차시 제목은 단원 앞쪽 계획 표에서 읽는다.
  `python scripts/split_by_lesson_headers.py --dir "D:\지도서\수학 3-2" --glob "*지도서_*단원.pdf" --units "곱셈,나눗셈,…" [--dry-run]`
- `scripts/apply_annual_plan.py` — 기존 분할기의 쪽 범위는 맞는데 제목이 깨지거나 묶음 차시(5~6차시)를 1차시로 셀 때(아이스크림 사회 등). 연간지도계획 PDF의 차시 목록과 분할 묶음 수가 같으면 순서대로 짝지어 제목·차시·단원 이름을 고친다(원본은 `groups.orig.json`).
  `python scripts/apply_annual_plan.py --groups "...\groups.json" --plan "...연간지도계획_1.pdf" --lessons 1-18 --unit "1. 사회 변화와 다양한 문화"`
- 천재 도덕 통합본은 차시 첫 쪽이 `1 4 … 차시 목표`로 시작한다. mapper 는 `도덕3_<단원>_<차시>_지도서.pdf` 이름을 찾으므로 그 이름으로 나눈다(1차시 파일에 단원 소개 쪽 포함).

## Output
- `output/<원본PDF이름>/groups.json`: 감지된 섹션, 그룹, 전략, 페이지 범위
- `output/<원본PDF이름>/pdf_splits/`: 분할된 PDF 묶음

