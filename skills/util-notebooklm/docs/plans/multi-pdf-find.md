# 설계 메모: 여러 PDF 한 번에 찾기 + `[p.N]` 자동 대조 (S7, ISSUE-004 둘째 줄)

- 작성: claude · 2026-11-27 · 설계 메모만(코드는 고치지 않음)
- 출처: `skills/util-notebooklm/ISSUES.md` ISSUE-004 "여러 PDF 를 한 번에 찾기(`find` 에 파일 여러 개), 답의 `[p.N]` 을 원문과 자동 대조하는 검사"
- 지금 코드(`nlm.py`)에서 확인한 것
  - `find <pdf> "<찾을 내용>"` 은 PDF 하나만 받는다(`cmd_find`, argparse 위치 인자 `pdf`·`query`).
  - `gemini_ask(..., work=...)` 에 `work` 폴더를 따로 주면 여러 개를 동시에 돌릴 수 있다(함수 설명에 적혀 있음). 지금 `cmd_find` 는 `work` 를 안 줘서 기본 `WORK` 하나를 쓴다.
  - 답 글 형식은 `FIND_PROMPT` 가 정한다: 인용마다 `[p.N]`(PDF 파일 쪽 번호), 마지막 줄에 `쪽: N, N-M`.
  - `page_refs(text)` 는 답에서 쪽 번호만 모은다(파일 이름은 모름). `cmd_pages --from <답.md>` 가 그걸 읽어 `fitz` 로 그 쪽만 잘라 낸다.

## 1. 여러 PDF 한 번에 찾기

### 모양 (기존 명령을 깨지 않게)
`find <pdf> "찾을 내용"` 은 그대로 두고 **새 명령**을 하나 더한다.

```
python nlm.py findall <pdf 또는 폴더>… --q "찾을 내용" [--model M] [--jobs 2]
```

- 왜 새 명령인가: `find` 의 위치 인자(`pdf`, `query`)를 `nargs="+"` 로 바꾸면 마지막 낱말이 질문인지 PDF 인지 헷갈린다. 새 명령이면 기존 사용법(SKILL.md 표)이 그대로다.
- 폴더를 주면 그 안의 `*.pdf` 를 이름순으로(하위 폴더는 보지 않음 — 추정: 지도서 폴더는 한 단계라서 충분).

### 하는 일 (함수 이름 수준)
1. `find_many(pdfs, query, model, jobs) -> list[FindResult]` 새 함수. `FindResult = (pdf, answer, used_model, error)`.
2. PDF 마다 `gemini_find(pdf, query, model, work=WORK / f"w{i}")` 를 부른다. `gemini_find` 는 지금 `work` 를 받지 않으므로 **`work=None` 인자만 더해 `gemini_ask` 로 넘긴다**(기본값이 `None` 이라 기존 호출은 그대로).
3. 동시에 돌리는 수 `--jobs` 기본 **2**, `concurrent.futures.ThreadPoolExecutor`. 무료 키의 동시 요청 한도는 **확인 필요**(2026-11-22 기록은 '붐빌 때 503' 뿐) — 처음엔 1~2 로 두고 시험해서 올린다.
4. 한 PDF 가 실패(`gemini_ask` 가 모든 모델 실패로 예외)해도 나머지는 계속하고, 끝에 실패 목록을 보여 준다.

### 저장 모양
- PDF 마다 기존과 같은 답 파일 `answers/<시각>_<pdf이름>.md` (머리 주석에 원본·질문·모델). → 기존 `pages <pdf> --from <답.md>` 가 **그대로** 동작한다(쪽 번호가 한 PDF 안의 번호라 헷갈리지 않음).
- 합친 목록 하나 `answers/<시각>_findall.md`: 질문, 그리고 PDF 별 `없음`/관련 쪽 요약표(파일 이름 · 관련 쪽 · 답 파일 경로). 쪽 번호만 있고 파일 이름이 없는 `[p.N]` 을 여러 PDF 가 섞어 쓰는 일을 피하려고 **답 본문을 한 파일로 이어 붙이지 않는다**.
- 화면 출력: 표만. 인용 원문은 답 파일에서 본다(토큰을 아끼려는 스킬 목적).

### 대안 (택하지 않음)
- PDF 를 `fitz` 로 하나로 합쳐 한 번에 묻기(쪽 번호 → 원래 파일·쪽 대응표 필요). Gemini 에 한 번만 보내서 빠르지만, 합친 크기가 Gemini 첨부 한도를 넘는지 **확인 필요**하고 인용이 어느 파일에서 왔는지 틀리면 찾기 어렵다. 위 방식이 단순·안전.

### 시험 (가짜로, 비밀값·실제 Gemini 없이)
`tests/test_nlm.py` 의 `FakeRun`·`ask` 도구를 그대로 쓴다.
- PDF 둘 + 가짜 답 → 답 파일 둘과 합친 목록이 생기고, `pages --from` 이 각 답에서 맞는 쪽을 읽는다.
- 한 PDF 만 모든 모델 실패 → 다른 PDF 결과는 남고 실패 목록에 이름이 나온다.
- `--jobs 2` 일 때 서로 다른 `work` 폴더를 쓴다(같은 폴더에 `doc.pdf` 를 덮어쓰지 않음).
- 폴더 인자: `*.pdf` 만, 이름순.

## 2. `[p.N]` 자동 대조 검사

Gemini 가 쪽 번호를 틀리게 적는 경우를 잡는 것이 목적이다(SKILL.md: "판단에 쓰기 전에 잘라 낸 원문 쪽으로 확인한다").

### 모양
```
python nlm.py check <pdf> --from <답.md> [--min-score 0.6]
```
토큰 0(Gemini 안 부름) — PDF 글자와 답 글만 비교한다. `fitz` 필요.

### 하는 일
1. 답 본문을 `[p.N]`·`[p.N-M]` 표시마다 **인용 덩어리**로 자른다. 새 함수 `quote_blocks(text) -> list[(pages, quote)]` (`PAGE_REF` 와 같은 정규식을 쓰되 쪽 번호와 그 뒤 인용 글을 함께 돌려줌). 끝의 `쪽: …` 줄은 제외.
2. 각 쪽의 글자를 `page_text(page)`(이미 있음)로 뽑아 `normalize()`(공백·`•` 같은 겹친 기호·제어문자 제거 — `CTL`·`DOUBLED` 정규식 재사용)를 거친다.
3. 인용의 앞 20~30자 조각 몇 개가 **적힌 쪽**에 있는지 본다 → 있으면 ✅.
4. 없으면 **다른 쪽**에서 찾아 본다 → 다른 쪽에 있으면 `⚠ p.N 이라 했지만 p.M 에 있음`, 어디에도 없으면 `❌ 원문에서 못 찾음`.
5. 결과를 `answers/<답 파일 이름>_check.md` 와 화면에 표로: `인용 앞부분 · 적은 쪽 · 실제 쪽 · 판정`.

### 조심할 점 (확인 필요)
- 글자가 거의 없는 '그림 쪽'(`is_low_text`, 한글 40자 미만)은 글자 대조가 안 된다 → 판정 `대조 불가(그림 쪽)`. 틀렸다고 하지 않는다.
- 인용이 한 쪽 끝~다음 쪽 처음에 걸치면 앞 조각만 맞을 수 있다 → 조각 여러 개 중 **일부만 맞아도 ✅**(`--min-score` 로 조절). 기준값 0.6 은 **추정**이라, 실제 지도서 답 3~5개로 시험해 정한다.
- Gemini 가 인용을 약간 바꿔 적는 경우(띄어쓰기·문장부호)가 있어 완전 일치가 아니라 정규화 뒤 부분 일치로 본다.
- 이 PC 에는 실제 지도서 PDF 가 저장소에 없다(저작물) → 시험은 `tests/test_nlm.py` 의 `guide_pdf` 처럼 **시험 안에서 만든 짧은 PDF** 로 한다.

### 시험 (가짜 PDF)
- 맞는 쪽 인용 → ✅ / 쪽 번호만 틀림 → `⚠`(실제 쪽 알려 줌) / 없는 글 → ❌ / 그림 쪽 → `대조 불가`.
- 공백·`•` 가 달라도 맞는 것으로 본다.
- `[p.N-M]` 범위 인용이 범위 안 아무 쪽에 있어도 ✅.

## 3. 만드는 순서(권장)와 영향
1. `check` 먼저(토큰 0, 혼자 돌아가고 `find` 를 안 고침, 위험이 가장 낮음). 새 함수 `quote_blocks`·`normalize`·`cmd_check` + 시험.
2. `findall` 은 그다음. 고치는 곳: `gemini_find` 에 `work=None` 인자, 새 `find_many`·`cmd_findall`, `main()` 에 부명령. 시험 추가.
3. 다 만들면 `SKILL.md` 사용법 표에 `findall`·`check` 두 줄, `ISSUES.md` ISSUE-004 둘째 줄을 해결로.
- `teacherlesson-assistant` 의 `notebook_sources.py` 가 `nlm` 함수(`page_text`·`write_source`·`whole_section` 등)를 가져다 쓴다. 위 계획은 **기존 함수의 시그니처를 바꾸지 않고 인자만 더하는** 방식이라 영향이 없을 것으로 본다(`notebook_sources.py` 를 직접 열어 확인하지는 않음 — **확인 필요**).
- 개인정보: `find`·`findall` 은 PDF 전체를 Gemini 에 보낸다. 학생 개인정보가 든 PDF 를 폴더째 넘기지 않도록 `findall` 시작 때 한 줄 경고를 보여 주는 것을 권한다.

## 4. 이 메모가 한 것·못 한 것
- 한 것: `nlm.py`·`tests/test_nlm.py` 를 읽고 이어 붙일 자리·함수 이름·시험 모양을 정함.
- 못 한 것: 실제 Gemini 호출·실제 지도서 PDF 로 시험(저작물·비밀값이라 안 함), 무료 키 동시 요청 한도, `notebook_sources.py` 영향 확인, `--min-score` 기준값.
