---
name: util-notebooklm
description: "긴 PDF(지도서·공문·규정집·매뉴얼·보고서)에서 필요한 부분만 찾아 프런티어 모델에 넘기는 공용 도구. Gemini CLI 로 관련 쪽·원문을 자동으로 찾고([p.N]), 그 쪽만 PDF 로 잘라 내고, NotebookLM 에 올릴 소스(쪽 표시 md + 그림 PDF)를 만들고, NotebookLM·북마클릿으로 받은 md 를 제목별로 자르고, 주제별 노트북 주소를 관리한다. 'PDF 에서 ~ 찾아줘', '이 문서 몇 쪽에 있어', 'NotebookLM 소스 만들어줘', '노트북에 물어볼 질문', '받은 md 잘라줘', '그 쪽만 잘라줘' 같은 요청, 그리고 큰 PDF 를 Claude 가 통째로 읽어야 할 것 같을 때 먼저 사용한다."
metadata:
  category: 공통 유틸
  status: 개발
  version: v0.1.0
  summary: 긴 PDF 를 Claude 가 통째로 읽지 않도록, Gemini CLI·NotebookLM 이 관련 쪽을 찾고 그 쪽만 잘라 프런티어 모델에 넘기는 찾기·잘라내기·소스 만들기 도구.
---

# util-notebooklm — 찾기는 Gemini·NotebookLM, 판단은 성능 높은 AI

큰 PDF 를 Claude 가 통째로 읽으면 토큰(AI 사용량)이 많이 든다. 그래서 일을 셋으로 나눈다.

1. **찾기** (싸고 빠름): Gemini CLI(`find`, 자동) 또는 NotebookLM(사람이 질문). 판단하지 않고 원문과 쪽 번호만 받는다.
2. **잘라내기** (토큰 0): 답에 나온 `[p.N]` 쪽만 원본 PDF 에서 잘라 낸다(`pages`).
3. **판단** (프런티어 모델 = Claude 처럼 성능이 높은 AI): 잘라 낸 몇 쪽만 넘겨 설계·비교·결정을 맡긴다.

## 언제 쓰나

- PDF 가 수십 쪽 이상이고 그중 일부만 필요할 때 → Claude 가 PDF 를 읽기 **전에** `find` 를 먼저 돌린다.
- 같은 문서 묶음에 자꾸 물을 때 → NotebookLM 노트북(`prep` 으로 소스 만들기, `nb` 로 주소 관리).
- **쓰지 않음:** 몇 쪽짜리 짧은 PDF(그냥 읽는 것이 싸다), 학생 개인정보가 든 문서(아래 주의).

## 사용법

이 폴더에서 `python nlm.py <명령>` 으로 실행한다(교사 PC 에서는 `C:\Python313\python.exe`). PDF 를 다루는 `pages`·`prep` 에는 PyMuPDF 라이브러리가 필요하다.

| 명령 | 하는 일 | 결과가 저장되는 곳 |
|---|---|---|
| `find <pdf> "찾을 내용" [--model M]` | Gemini CLI 가 관련 원문을 `[p.N]`(PDF 쪽 번호)과 함께 인용. 한 번에 40~70초 | `answers/` |
| `pages <pdf> 4,7-8` 또는 `pages <pdf> --from 답.md` | 그 쪽만 새 PDF 로. `--from` 은 답 글의 `[p.N]`·`[p.N-M]`·`PDF 파일 N쪽` 표시를 모은다. 범위 밖 쪽은 빼고, 남는 쪽이 없으면 멈춘다 | `pages/` |
| `verify <pdf> <답.md>` | 답의 `[p.N]` 인용문이 **정말 그 쪽 원문에 있는지** 대조(공백·문장부호·줄바꿈·영문 대소문자 무시, `…`·`[중략]` 로 줄인 인용은 조각마다). 맞음·다른 쪽에 있음(실제 쪽 알려 줌)·원문에 없음·없는 쪽·너무 짧아 대조 안 함(정리 후 8글자 미만)으로 알려 주고, **원문에 없거나 PDF 에 없는 쪽이 있으면 종료 코드 1**. 읽기만 함(PyMuPDF 필요) | 화면 출력만 |
| `prep <pdf…> [--images auto\|all\|none] [--title 제목]` | NotebookLM 에 올릴 소스: 쪽마다 `〔p.N〕` 을 붙인 글(`<PDF이름>.md`) + 흑백 그림 PDF(`<PDF이름>_그림.pdf`). `auto`(기본)는 글자가 거의 없는 쪽만, `all` 은 모든 쪽, `none` 은 그림 없음. 제목은 안 주면 PDF 이름. 50만 단어 한도에 가까우면 경고 | `sources/` |
| `split <받은.md> [--pattern 정규식]` | 북마클릿 등으로 받은 md 를 제목 줄(`#`, `**`)에서 자르기. `--pattern` 을 주면 그 정규식이 든 제목에서만 자른다. 첫 제목 앞의 글은 버림. 조각 이름은 `01_제목.md` 꼴 | `notes/<받은 파일 이름>/` |
| `nb list` / `nb add <주제> <주소> [--note 설명]` / `nb open <주제> [--q "찾을 내용"]` | 노트북 목록 관리. `open` 은 찾기 전용 질문을 복사하고 노트북을 연다(윈도우 전용) | `notebooks.json` |

- 저장 위치는 모두 데이터 폴더 `내 문서\my-skills-data\util-notebooklm\` 아래다. `--out` 으로 바꿀 수 있다. 다만 `find`·`pages` 의 `--out` 은 **파일 경로**, `prep`·`split` 의 `--out` 은 **폴더**다.
- `nb add` 의 주소는 `https://notebooklm.google.com/` 으로 시작해야 한다.

### 다른 스킬에서 가져다 쓰기

- 함수: `page_text`, `write_source`, `whole_section`(PDF→소스), `split_text`, `page_refs`, `notebook_url`, `gemini_find`, `gemini_ask`
- PyMuPDF(`fitz`)는 PDF 함수 안에서만 불러온다. 그래서 `split_text`·`notebook_url` 만 쓰는 쪽은 기본 Python 이면 된다.
- 예: `teacherlesson-assistant` 의 `notebook_sources.py`

## 준비

- Gemini CLI 설치: `npm i -g @google/gemini-cli`
- API 키(서비스를 쓰는 비밀 번호): 중앙 `.env` 에서 `UTIL_NOTEBOOKLM__GEMINI_API_KEY` → `GEMINI_API_KEY` → `GEMINI_API_KEY_FROM_VAULT_NOTE` 순서로 찾는다.
  - 키가 있으면 작업 폴더(`gemini_work/.gemini/settings.json`)에서만 API 키 방식을 쓴다. 전역 Gemini 설정과 확장은 건드리지 않는다(`-e none` 으로 확장 끔).
  - 키가 없으면 그 PC 의 구글 로그인을 쓴다.
- 기본 모델은 `gemini-3.8-flash` (무료 키는 pro 모델 한도가 0). 실패하거나 붐비면 코드에 적힌 다른 모델로 차례로 다시 시도한다.
- `nlm.gemini_ask(..., model_timeout=45)` 처럼 모델 하나를 기다리는 최대 시간을 따로 줄일 수 있다. 돌려주는 값은 `(답변, 실제로 답한 모델)` 이다.

## 주의

- **학생·학부모 개인정보가 든 문서는 Gemini·NotebookLM 에 넣지 않는다**(구글 서버로 감). `find` 는 PDF 파일 전체를 Gemini 에 보낸다.
- 지도서·교재는 저작물이다. 노트북을 공개로 공유하지 않는다.
- Gemini 의 인용은 맞는 경우가 많지만(2026-11-22 시험 3/3 정확), 판단에 쓰기 전에 잘라 낸 원문 쪽으로 확인한다.
- NotebookLM 은 공개 API(프로그램이 접속하는 통로)가 없어 올리기·받아오기는 사람이 한다.

## 문서

- [ISSUES.md](ISSUES.md) — 문제·해결 기록, 할 일
