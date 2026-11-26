# teacherlesson-guide 이슈 로그

> 이 스킬에서 생긴 문제와 해결 과정, 진행 중인 일, 할 일을 기록한다.
> 새 항목은 해당 절의 맨 위에 추가하고, 해결되면 '🟢 해결됨'으로 옮긴다.
> 2026-11-22 guide-splitter·guide-mapper·수업 비서의 지도서 받기를 이 스킬로 합쳤다. 그 전 기록은 teacherlesson-assistant ISSUES 의 '요청됨 (2026-11-20)' 절.

## 🔵 진행 중

### ISSUE-004: 옛 폴더 이름으로 mapper 결과 100개가 다시 커밋됨 (2026-11-25 발견)
- **상태**: 🟢 해결됨 (2026-11-25, 교사 요청으로 정리)
- **조치**: 100개(2026-04 3-1 시절 스냅샷)를 저장소에서 지우고 루트 `.gitignore`에 옛 폴더 이름을 넣어 다시 안 올라가게 함. 저장소 안에는 이 경로를 쓰는 코드·문서가 없었음. 지운 파일은 커밋 737f279에 남아 있어 `git show 737f279:<경로>`로 되살릴 수 있음. **학교 PC는 다음에 받을 때 이 옛 폴더가 지워짐** — 이관 프로그램(`semester_rollover`)이 이 경로를 쓰고 있었다면 새 지도서 처리(`teacherlesson-guide/mapper/generated_rows/`)로 다시 만들면 됨
- **증상**: 커밋 737f279("1123", 학교 PC)에서 `skills/teacherlesson-guide-mapper/generated_rows/`(3.6MB, json 100개)가 저장소에 들어감 → 지운 스킬 이름의 폴더가 되살아나 `python tools/build_catalog.py --check` 가 "SKILL.md 없음"으로 실패
- **원인**: 2026-11-22 합칠 때 `git mv` 는 추적 파일만 옮겨, 학교 PC 에는 추적 안 되던 옛 결과 폴더가 남음 → 전체 추가(add -A)로 다시 올라감

### ISSUE-002: 저장소 기록에 출판사 지도서 분할 PDF 가 남아 있음 (2026-11-22)
- **상태**: 🔵 진행 중 (사람 결정 필요)
- **증상**: 옛 splitter 의 `tmp_output_save/art/pdf_splits/*.pdf`(미술 지도서 분할본 15개, 약 72MB)와 `tmp_*` 시험 결과가 2026-04-14 부터 공개 저장소에 커밋돼 있었음
- **조치**: 2026-11-22 추적 해제(`git rm --cached`, 파일은 PC 에 남김) + `.gitignore`
- **남은 일**: 지난 커밋 기록에서도 지우려면 기록 다시 쓰기(filter-repo)와 강제 푸시가 필요 → 저장소 주인 결정

## 📌 백로그

### ISSUE-33: 진도표 행 올리기에서 Enter 두 번이면 그 과목의 기존 행이 지워짐 (2026-11-26)
- **상태**: 📌 백로그 (바꿀지 교사 결정 필요)
- **증상**: `map_general_guides_to_sheet.py` 를 터미널에서 옵션 없이 실행하면 "업로드할까요? [Y/n]"(Enter=올리기) 다음 업로드 방식 질문의 Enter 기본값이 2번(만든 과목의 기존 행을 지우고 업로드). 지워지는 행에는 완료 표시한 지난 행도 들어갈 것(추정). 코드를 읽어 확인했고 실제 시트에서는 실행하지 않음
- **원인**: `confirm_upload_action` 의 기본값이 올리기·교체. 또 `upload_rows_to_sheet` 는 먼저 지우고 나서 붙이므로, 붙이기가 실패하면 지운 채로 남을 수 있음(추정)
- **해결/조치**: SKILL.md 에 경고만 추가. 기본값을 '올리지 않기'로 바꾸는 것을 권함
- **관련 파일**: `mapper/map_general_guides_to_sheet.py`(`confirm_upload_action`), `mapper/sheet_uploader/core.py`(`upload_rows_to_sheet`)

### ISSUE-003: 지도서 처리 남은 일 (수업 비서에서 옮김, 2026-11-22)
- guide-mapper 대체 매칭: 3-1 국어를 다시 만들면 독서·매체 행이 3-2 PDF를 가리킴(이 PC에 3-1 PDF 없음). 학년·학기가 다르면 대체 매칭에서 빼기
- `split_by_lesson_headers` 재실행 시 예전 `pdf_splits` 조각이 남음 / `apply_annual_plan` 의 `groups.orig.json` 이 첫 분할 것만 보관
- 아이스크림 자동 로그인 불안정: 크롬 저장 비밀번호가 사람 클릭 전에는 칸에 안 채워질 때가 있음 (지도서 파일 자체는 로그인 없이 받아짐)
- 음악 지도서 분할본(`D:\지도서\음악\pdf_splits`)이 이 PC에 없음 — 진도표 경로는 그곳을 가리킴
- mapper 의 `.env` 대체 경로가 옛 `teacher-schedule\.env` 를 가리킴 → 중앙 .env 만 쓰도록 정리

### ISSUE-001: 분할 자동화 — "쪽 머리 글 → Gemini → 쪽 범위" (2026-11-22, 교사 요청: 만들 때만 토큰, 쓸 때는 0) ← 다음에 할 큰 일
- **시험 결과 (2026-11-22)**: 국어 3-2 4단원(52쪽)
  - PDF 통째로 Gemini 에 줌 → 458초, 개관 1개만(0/9). 무료 모델이 붐벼 lite 까지 내려감 → **PDF 통째는 안 씀**
  - **쪽마다 앞 160자 글만**(8.5천 자) 줌 → **9/9 정답**(lite 모델로도). 시간 367초는 대부분 붐빔 대기(모델마다 120초 기다림) — 글이 작으니 모델별 대기를 30~45초로 줄이면 됨
- **현 PC 시험 (2026-11-23)**:
  - `auto_split.py` 초안을 추가하고 3-1 수학 1단원 지도서 35쪽을 처리함. PyMuPDF 글자 추출은 35/35쪽 성공, Gemini가 쪽 시작 후보 8개를 반환함.
  - 기존 분할 결과와 대조하자 차시 번호를 순서대로 추정한 오답이 드러남. 그래서 진도표 차시 목록과 번호·쪽을 대조하지 못하면 Markdown 생성/게시를 막도록 변경. 제목 표현은 진도표·지도서 간 달라질 수 있어 페이지 안 핵심 단어로 검증함.
  - 진도표 `build_units.py --all` 읽기 완료. 3-1 첫 수학 단원 9개 차시 목록으로 재실행하자 PDF 시작 쪽 9개가 기존 `groups.json` 경계와 모두 일치했고, 제목 표기 공백·동그라미 숫자 차이를 정규화해 통과함. `prepare_lessons.lesson_section()`으로 2차시 글 5,887자를 실제로 가져오는 것도 확인함. 결과는 현재 PC Documents 데이터 폴더에 저장했으며 OneDrive 공유 여부는 별도 설정 전까지 확인되지 않음.
  - 3-2 수학 1단원(56쪽)도 실제 자료로 연결: 진도표 차시 12개, Gemini 시작 쪽·제목 검증 12/12 통과, NotebookLM Markdown을 수업 비서 `notebooklm/수학/1._곱셈.md`에 게시. `lesson_section()`이 1·2·12차시 본문(2,322·6,050·5,714자)을 가져오는 것 확인.
  - 이 PC는 Python 3.11 + Selenium/PyMuPDF 사용 가능, 데이터 폴더는 로컬 Documents. 처음엔 `units/`가 비어 있었지만 `build_units.py --all`로 3-1·3-2 진도표 메타데이터를 생성함. OneDrive 공유 폴더는 이 PC에서 찾지 못함.
  - 다운로드 실행: 수학 3-2 지도서 7개, 사회 지도서·연간계획 4개, 국어 3-2 PDF 10개(총 약 325MB)를 `D:\지도서`에 받았고 PyMuPDF로 모두 열림(21/21, PDF 오류 없음). 도덕 3-2는 기존 `D:\지도서\도덕 3`에서 해당 분할본을 확인함.
  - 국어는 미래엔 목록 확인 뒤 ChromeDriver 재연결이 120초 시간 초과. 확인된 DVD URL로 기존 Range ZIP 추출 함수를 이용해 10개를 받음. 재발 방지를 위해 `--list` 때 미래엔 URL 저장, 실제 받기 때 재사용하도록 개선함.
  - 국어 출판사 설정이 빠져 있어 미래엔으로 추가함(config.example + 이 PC config). Google 계정 힌트는 교사가 준 `ilov` 접두사로 이 PC config에만 설정함. T셀파 목록 확인은 ChromeDriver 재연결 시간 초과로 못 했지만 필요한 도덕 3-2 분할본은 이미 있음.
- **만들 것** (`teacherlesson-guide/auto_split.py`, Claude 토큰 0으로 돌아감)
  1. `guide_download.py` 로 받은 PDF 마다 쪽 머리 글 뽑기(PyMuPDF, 무료)
  2. Gemini(`nlm.gemini_ask`, 글 파일)에게 "차시별 시작 쪽·차시 제목" JSON 받기. 단원 개관·평가 쪽도 함께
  3. 검사(쪽 순서, 제목 낱말이 그 쪽 글에 있는지, 진도표 차시 수와 맞는지). 틀리면 기존 규칙(splitter `LESSON_START`, notebook_sources 의 `KOREAN_LESSON`/`STAGE`)으로 대신
  4. **물리 분할 안 함**: 진도표 `pdf파일`(원본) + `시작페이지`/`끝페이지` 만 채움 → 진도 서버 `/api/pdf` 가 이미 쪽 범위로 잘라 보여 줌
  5. 같은 표로 차시별 글 md(NotebookLM 소스·🌙 수업 준비 입력)를 만들어 OneDrive 에 둠 → 학교 PC 는 PDF 없이 준비 가능
- **경로**: 진도표 PDF 경로를 PC 마다 다른 지도서 위치에서도 맞게 (`%GUIDE_ROOT%\수학 3-2\…` 처럼 적고 PC 마다 기본값 `D:\지도서`) — 서버는 이미 `os.path.expandvars` 로 읽음
- 무료 Gemini 붐빔 대비: 학기 초 한 번 뒤에서 돌리면 되므로 시간은 중요하지 않음. `gemini_ask` 에 모델별 대기 시간 인자 추가

## 🟢 해결됨

### ISSUE-32: `.gitignore` 가 분할기 기본 결과 폴더(`output/`)의 지도서 PDF 를 막지 않음 (2026-11-26, 2026-11-27 해결)
- **상태**: 🟢 해결됨 (T90)
- **증상**: `split_subunits_from_plan_table.py` 의 `--out-dir` 기본값은 `output`. 저장소 안에서 실행하면 `splitter/output/…/pdf_splits/*.pdf` 와 `groups.json` 이 생기는데 막히지 않았다(저작물이 올라갈 수 있음 — ISSUE-002 와 같은 종류).
- **원인**: `.gitignore` 는 `tmp*/`·`generated_rows/`·`.cache/` 등 정해진 이름만 막았다.
- **해결**: 이 폴더 `.gitignore` 에 `output/`·`pdf_splits/`·`groups.json`·`*.pdf`·`*.part` 추가(요청보다 넓게: 이 폴더 안의 지도서 PDF 와 받는 중 임시 파일도 막음). 꼭 올려야 하는 PDF 는 `git add -f <파일>` 로 한 개씩 올린다.
- **확인**: `git check-ignore -v` 로 막혀야 할 11개 경로는 막히고 코드·문서 8개는 안 막힘. 이미 추적 중인 파일 중 새로 걸리는 것 없음(`git ls-files -ci --exclude-standard`). 다른 스킬 폴더는 영향 없음.
- **관련 파일**: `.gitignore`, `splitter/scripts/split_subunits_from_plan_table.py`

### ISSUE-005: `auto_split.json_object` 가 설명 글의 중괄호에 걸림 (2026-11-25 시험으로 발견, 2026-11-26 해결)
- **상태**: 🟢 해결됨 (T67)
- **증상**: Gemini 답에서 JSON 앞이나 뒤 설명에 `{` `}` 가 있으면(예: "참고 {예시} 입니다.") 첫 `{` 부터 마지막 `}` 까지를 통째로 읽어 `JSONDecodeError` 가 났다. `main()` 이 `json_object` 호출을 감싸지 않아 "JSON을 찾지 못했습니다" 같은 안내 없이 파이썬 오류 출력으로 멈추고, 쪽 색인 분석(Gemini 호출)을 처음부터 다시 해야 했다.
- **원인**: `text.find("{")` ~ `text.rfind("}")` 구간을 그대로 `json.loads`.
- **해결**: `{` 위치마다 `json.JSONDecoder.raw_decode` 로 JSON 한 덩어리씩 읽어 `lessons` 목록이 있는 첫 덩어리를 쓴다. 읽은 덩어리 안쪽의 `{` 는 건너뛰어 안쪽 객체를 답으로 착각하지 않는다. 오류 문구("JSON을 찾지 못했습니다" / "lessons 목록이 없습니다")는 그대로, 읽을 수 있는 JSON 이 전혀 없으면 첫 `JSONDecodeError` 를 올린다.
- **시험**: `tests/test_auto_split.py` — xfail 표시를 지우고 사례 추가(앞뒤 설명·붙은 중괄호·문자열 속 중괄호·lessons 없는 덩어리 건너뛰기·안쪽 객체 거부). 소스를 일부러 틀리게 한 변이 3가지를 모두 시험이 잡음
- **남은 것**: `teacherlesson-assistant` 의 `prepare_lessons.parse_flow` 도 같은 방식(ISSUE-031) — 별도 일(T68)
- **관련 파일**: `auto_split.py`, `tests/test_auto_split.py`
