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

학기 초에 한 번 하는 일이다. 자세한 설정(옵션)은 각 하위 폴더의 README 를 본다. 아래 명령은 이 폴더에서 실행한다.

```
download/  출판사 사이트 → D:\지도서\<과목> <학년-학기>\*.pdf
splitter/  PDF → <폴더>/groups.json + pdf_splits/*.pdf   (차시·단원별로 나눔)
mapper/    groups.json·PDF → 진도표 행(mapper/generated_rows/) → 구글 시트에 올림
           → teacherlesson-schedule 의 semester_rollover.py 가 진도표에 붙임
```

`groups.json` 은 "어느 차시가 몇 쪽부터 몇 쪽까지인지" 적은 파일이다. '차시'는 한 단원 안의 수업 한 번 분량이다.

## 1. 받기 — `download/guide_download.py`

```powershell
python download\guide_download.py 수학 사회            # 받기
python download\guide_download.py 수학 --list          # 목록만 보기
python download\guide_download.py 사회 --with-plan     # 연간지도계획도 받기
```

- selenium(크롬을 자동으로 움직이는 라이브러리)이 깔린 Python 으로 실행한다.
- 수업 비서(`teacherlesson-assistant`)의 크롬 프로필·포트·출판사 설정을 같이 쓴다.
- 저장 위치는 기본 `D:\지도서`. 환경 변수 `GUIDE_ROOT` 나 `--root` 로 바꾼다.
- 출판사별 방법(아이스크림, 미래엔 ZIP 에서 필요한 파일만 받기, 천재 T셀파)은 [download/README.md](download/README.md).

## 2. 나누기 — `splitter/` ([README](splitter/README.md))

먼저 결과만 보고(`--dry-run`), 확인한 뒤 저장한다(`--save`).

```powershell
python splitter\scripts\split_subunits_from_plan_table.py --pdf "D:\지도서\지도서.pdf" --out-dir "D:\지도서\나눈결과" --dry-run
```

어떤 지도서에 어느 것을 쓰나:

| 경우 | 쓰는 것 |
|---|---|
| 보통 지도서 | `split_subunits_from_plan_table.py` — 차례·개관·지도 계획 표·차시 계획 글에서 나눌 기준을 고르고, 깨진 제목은 시작 쪽의 제목으로 바로잡음. 설정: `--scan-pages`, `--page-offset`, `--z-col`, `--split-level detail` |
| 쪽 머리에 차시 표시가 있는 지도서(아이스크림 수학 등) | `split_by_lesson_headers.py --dir … --glob … --units …` |
| 쪽 범위는 맞는데 제목·묶음 차시가 틀림(아이스크림 사회) | `apply_annual_plan.py --groups … --plan 연간지도계획.pdf --lessons 1-18 --unit "단원 이름"` |
| 천재 도덕 통합본 | 차시 첫 쪽이 `1 4 … 차시 목표` 모양. mapper 가 찾는 이름 `도덕3_<단원>_<차시>_지도서.pdf` 로 나눔 |

- 표의 스크립트는 모두 `splitter\scripts\` 에 있다.
- 결과: `<원본이름>/groups.json`, `<원본이름>/pdf_splits/`

### 2-A. 수업 비서용 글 자료 만들기 — `auto_split.py`

PDF 를 나누는 대신, 원본 PDF 의 글을 쪽마다 정리한 Markdown(글 파일)으로 만들어 `teacherlesson-assistant` 가 차시 단위로 가져가게 한다.

```powershell
python auto_split.py "D:\지도서\지도서.pdf" --subject 수학 --unit "6단원" `
  --from-page 120 --to-page 168 --lesson-list-json lessons.json --publish-to-assistant
```

- Gemini 에는 각 쪽의 앞부분과 `차시`가 든 줄만 모은 색인을 보낸다. PDF 전체는 보내지 않는다.
- **진도표의 차시 목록이 꼭 필요하다.** 목록이 없으면 Gemini 를 부르지 않는다.
  - 수업 비서 데이터 폴더에 `units/<과목>__<단원>.json` 이 있으면 자동으로 쓴다.
  - 없으면 먼저 `python ..\teacherlesson-assistant\build_units.py --all` 을 실행하거나,
  - `--lesson-list-json lessons.json` 으로 `{"lessons":[{"from":1,"to":1,"title":"차시 제목"}]}` 모양의 목록을 준다.
- 차시 번호·제목·시작 쪽을 대조해 하나라도 어긋나면 Markdown 을 만들지 않고, 수업 비서 폴더에도 쓰지 않는다. 같은 폴더의 `page_heads.md`·`analysis.json` 을 확인한다.
- 결과는 기본으로 원본 PDF 옆 `auto_split/<파일명>/` 에 생긴다.
- `--publish-to-assistant` 를 붙이면 이 PC 의 `my-skills-data/teacherlesson-assistant` 아래 `notebooklm/<과목>/<단원>.md` 에도 저장한다. 이 위치가 OneDrive 공유 폴더가 아니면 다른 PC 와 맞춰지지 않는다.
- 이미지뿐이거나 뽑힌 글자가 적은 쪽은 글자 인식(OCR)을 하지 않고 '확인 필요' 표시를 붙인다.
- `--inspect-only` 로 색인만 먼저 만들 수 있다. 이 명령은 PDF 를 나누거나 시트에 올리지 않는다.

## 3. 진도표 행 만들기 — `mapper/` ([README](mapper/README.md))

```powershell
python mapper\map_general_guides_to_sheet.py                          # D:\지도서 에서 과목을 자동으로 찾아 행 만들기
python mapper\map_general_guides_to_sheet.py --subject 국어 --grade 3-2   # 학기를 정하려면 과목도 함께
```

> ⚠ **구글 시트를 바꿀 수 있다.** `map_general_guides_to_sheet.py`(`mapper\실행.bat` 도 이것)는 `--upload` 없이 실행해도 터미널에서 미리보기 뒤에 "업로드할까요?"를 묻는다.
> **Enter 를 누르면 올리기로 넘어가고, 다음 질문에서 또 Enter 를 누르면 이번에 만든 과목의 기존 행을 지우고 올린다.** 미리보기만 하려면 첫 질문에 `n`.
> 두 mapper 스크립트 모두 `--cleanup` 을 붙이면 `--upload` 가 없어도 시트에 올린다.

- 만든 결과는 `mapper/generated_rows/<시각>/` 에 남는다.
- `--grade` 는 `--subject` 나 `--all-presets` 와 함께 써야 적용된다. 정하지 않으면 도구에 적힌 기본값(국어·수학·사회·과학은 3-1)을 쓴다.
- `mapper\map_guides_to_sheet.py` — 국어·도덕 전용.
- `mapper\sheet_uploader\upload_generated_rows.py` — 만들어 둔 JSON 을 시트에 올림(실행하면 바로 올림).
- 시트에 붙이기·지난 학기 정리는 `teacherlesson-schedule/semester_rollover.py`.

## 새 출판사·새 지도서는 "노트북 먼저"

나누는 규칙을 새로 만들면 AI 사용량(토큰)이 많이 든다. 규칙이 안 맞는 새 지도서는 먼저:

1. `util-notebooklm` 의 `nlm.py find <pdf> "차시별 시작 쪽 번호와 차시 제목 표"` 로 Gemini 에게 쪽 번호 표를 받는다.
2. 그 쪽 번호로 `nlm.py pages` 나 짧은 스크립트를 써서 자른 뒤, mapper 가 읽는 모양(`groups.json`)으로 맞춘다.
3. 그래도 안 맞을 때만 splitter 규칙을 고친다.

## 다른 스킬과의 관계

- `teacherlesson-schedule` — 옛 방식의 구글 시트 진도표·조정 서버. 이 스킬이 올린 행을 받는다.
- `teacherlesson-assistant` — 수업 중에 쓰는 화면. 진도 원본은 이제 Supabase(인터넷 데이터베이스)이며, 차시 지도서 PDF 를 보여 주고 단원 개관·NotebookLM 소스를 만든다.
- `teacherlesson-workspace` — `scripts/sync_semester2.py` 가 구글 시트의 2학기 진도를 Supabase 로 옮긴다.
- `util-notebooklm` — 지도서에서 찾기·쪽 잘라내기(여러 스킬이 같이 씀).

## 주의

- 지도서 PDF·나눈 결과는 저작물이다. **저장소에 올리지 않는다.**
- 이 폴더의 `.gitignore` 가 막는 것은 `tmp*/`, `generated_rows/`, `.cache/` 같은 정해진 이름뿐이다. 예를 들어 `output/` 폴더의 `pdf_splits` 는 막지 않는다. 결과는 `D:\지도서` 아래처럼 저장소 밖에 둔다.

## 문서

- [ISSUES.md](ISSUES.md), [splitter/README.md](splitter/README.md), [mapper/README.md](mapper/README.md)
