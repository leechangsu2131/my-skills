---
name: teacherlesson-guide
description: "교사용 지도서 처리 한 묶음: 출판사 사이트에서 지도서 PDF 받기(download) → 차시·단원별로 나누기(splitter) → 진도표 행 만들기·시트 업로드(mapper). '지도서 받아줘', '지도서 나눠줘', '지도서 분할', '진도표 행 만들어줘', '새 학기 진도표', 'groups.json', 'pdf_splits' 같은 요청에 사용한다. 지도서에서 특정 내용만 찾을 때는 util-notebooklm 을 먼저 쓴다."
metadata:
  category: 수업·교사 도구
  status: 운영
  version: v1.0.0
  summary: 출판사 지도서 PDF 받기 → 차시별 분할 → 진도표 행 생성·업로드를 한 스킬로 묶은 지도서 처리 흐름. (옛 guide-splitter·guide-mapper·수업 비서의 지도서 받기를 합침)
---

# 지도서 처리 (teacherlesson-guide)

학기 초에 한 번 도는 흐름이다. 각 단계의 자세한 옵션은 하위 폴더 README.

```
download/  출판사 사이트 → D:\지도서\<과목> <학년-학기>\*.pdf
splitter/  PDF → <폴더>/groups.json + pdf_splits/*.pdf   (차시·단원별)
mapper/    groups.json·PDF → 진도표 행(generated_rows/) → 시트 업로드
           → teacherlesson-schedule(semester_rollover)가 진도표에 붙임
```

## 1. 받기 — `download/guide_download.py`

`C:\Python313\python.exe download\guide_download.py 수학 사회 [--list] [--with-plan]` (selenium)
수업 비서(`teacherlesson-assistant`)의 크롬 프로필·포트·출판사 설정을 같이 쓴다. 출판사별 방법(아이스크림·미래엔 ZIP 부분 받기·천재 T셀파)은 [download/README.md](download/README.md).

## 2. 나누기 — `splitter/` ([README](splitter/README.md))

- 범용: `python splitter\scripts\split_subunits_from_plan_table.py --pdf "지도서.pdf" --out-dir out --dry-run` → 확인 뒤 `--save`. 차례·개관·지도 계획 표·차시 계획 글에서 분할 기준을 고르고 깨진 제목을 시작 쪽 제목으로 보정. 옵션 `--scan-pages`, `--page-offset`, `--z-col`, `--split-level detail`.
- 쪽 머리에 차시 표시가 있는 지도서(아이스크림 수학 등): `scripts/split_by_lesson_headers.py --dir … --glob … --units …`
- 쪽 범위는 맞는데 제목·묶음 차시가 틀릴 때(아이스크림 사회): `scripts/apply_annual_plan.py --groups … --plan 연간지도계획.pdf`
- 천재 도덕 통합본: 차시 첫 쪽이 `1 4 … 차시 목표`. mapper 가 찾는 `도덕3_<단원>_<차시>_지도서.pdf` 이름으로 나눈다.
- 결과: `<원본이름>/groups.json`, `<원본이름>/pdf_splits/`

## 3. 진도표 행 — `mapper/` ([README](mapper/README.md))

- `python mapper\map_general_guides_to_sheet.py` — `D:\지도서` 자동 감지, 전 과목 행 생성, `mapper/generated_rows/<시각>/` 스냅샷. 국어 학기 인자 `--grade 3-2`.
- `mapper\map_guides_to_sheet.py` — 국어·도덕 전용. `mapper\sheet_uploader\` — 만든 JSON 업로드.
- 시트에 붙이기·지난 학기 정리는 `teacherlesson-schedule/semester_rollover.py`.

## 새 출판사·새 지도서는 "노트북 먼저"

분할 규칙을 새로 짜면 토큰이 많이 든다. 규칙이 안 맞는 새 지도서는 먼저:
1. `util-notebooklm` 의 `nlm.py find <pdf> "차시별 시작 쪽 번호와 차시 제목 표"` 로 Gemini 에게 쪽 번호 표를 받고,
2. 그 쪽 번호로 `nlm.py pages` 나 짧은 스크립트로 자른 뒤 mapper 형식(groups.json)으로 맞춘다.
3. 그래도 안 맞을 때만 splitter 규칙을 고친다.

## 다른 스킬과의 관계

- `teacherlesson-schedule` — 진도표 원본·조정 API. 이 스킬의 결과를 받는다.
- `teacherlesson-assistant` — 수업 중 화면. 분할된 차시 PDF 를 진도 서버 `/api/pdf` 로 보여 주고, 단원 개관·NotebookLM 소스를 만든다.
- `util-notebooklm` — 지도서에서 찾기·쪽 잘라내기(공용).

## 주의

- 지도서 PDF·분할 결과는 저작물이다. 저장소에 올리지 않는다(`.gitignore`: `tmp*/`, `generated_rows/`). 결과는 `D:\지도서` 와 하위 폴더 출력에만 둔다.

## 문서
- [ISSUES.md](ISSUES.md), [splitter/README.md](splitter/README.md), [mapper/README.md](mapper/README.md)
