---
name: util-notebooklm
description: "긴 PDF(지도서·공문·규정집·매뉴얼·보고서)에서 필요한 부분만 찾아 프런티어 모델에 넘기는 공용 도구. Gemini CLI 로 관련 쪽·원문을 자동으로 찾고([p.N]), 그 쪽만 PDF 로 잘라 내고, NotebookLM 에 올릴 소스(쪽 표시 md + 그림 PDF)를 만들고, NotebookLM·북마클릿으로 받은 md 를 제목별로 자르고, 주제별 노트북 주소를 관리한다. 'PDF 에서 ~ 찾아줘', '이 문서 몇 쪽에 있어', 'NotebookLM 소스 만들어줘', '노트북에 물어볼 질문', '받은 md 잘라줘', '그 쪽만 잘라줘' 같은 요청, 그리고 큰 PDF 를 Claude 가 통째로 읽어야 할 것 같을 때 먼저 사용한다."
metadata:
  category: 공통 유틸
  status: 개발
  version: v0.1.0
  summary: 긴 PDF 를 Claude 가 통째로 읽지 않도록, Gemini CLI·NotebookLM 이 관련 쪽을 찾고 그 쪽만 잘라 프런티어 모델에 넘기는 찾기·잘라내기·소스 만들기 도구.
---

# util-notebooklm — 찾기는 Gemini·NotebookLM, 판단은 프런티어 모델

큰 PDF 를 Claude 가 통째로 읽으면 토큰이 많이 든다. 이 스킬은 일을 셋으로 나눈다.

1. **찾기** (싸고 빠름): Gemini CLI(`find`, 자동) 또는 NotebookLM(사람이 질문). 판단 없이 원문과 쪽 번호만 받는다.
2. **잘라내기** (토큰 0): 답에 나온 `[p.N]` 쪽만 원본 PDF 에서 잘라 낸다(`pages`).
3. **판단** (프런티어 모델): 잘라 낸 몇 쪽만 Claude 등에 넘겨 설계·비교·결정을 맡긴다.

## 언제 쓰나

- PDF 가 수십 쪽 이상이고 그중 일부만 필요할 때 → Claude 가 PDF 를 읽기 **전에** `find` 를 먼저 돌린다.
- 같은 문서 묶음에 자꾸 물을 때 → NotebookLM 노트북(`prep` 으로 소스 만들기, `nb` 로 주소 관리).
- 쓰지 않음: 몇 쪽짜리 짧은 PDF(그냥 읽는 게 싸다), 학생 개인정보가 든 문서(아래 주의).

## 사용법 (`C:\Python313\python.exe nlm.py …`, PyMuPDF 필요)

| 명령 | 하는 일 |
|---|---|
| `find <pdf> "찾을 내용" [--model M]` | Gemini CLI 가 관련 원문을 `[p.N]` 과 함께 인용. 답은 데이터 폴더 `answers/` 에 저장. 한 번 40~70초 |
| `pages <pdf> 4,7-8` / `pages <pdf> --from 답.md` | 그 쪽만 새 PDF 로 (`pages/`) |
| `prep <pdf…> [--images auto\|all\|none]` | NotebookLM 소스: 쪽마다 `〔p.N〕` 붙인 md + 글자 없는 쪽 흑백 PDF (`sources/`) |
| `split <받은.md> [--pattern 정규식]` | 북마클릿 등으로 받은 md 를 제목(#, **) 단위로 자르기 (`notes/`) |
| `nb list` / `nb add <주제> <주소>` / `nb open <주제> --q "찾을 내용"` | 노트북 목록. open 은 찾기 전용 질문을 복사하고 노트북을 연다 |

다른 스킬에서 가져다 쓰기: `page_text`, `write_source`, `whole_section`(PDF→소스), `split_text`, `page_refs`, `notebook_url`, `gemini_find`. `fitz` 는 PDF 함수 안에서만 불러오므로 `split_text`·`notebook_url` 만 쓰는 쪽은 기본 파이썬이면 된다. 예: `teacherlesson-assistant` 의 `notebook_sources.py`.

## 준비

- Gemini CLI(`npm i -g @google/gemini-cli`). 키: 중앙 .env 의 `UTIL_NOTEBOOKLM__GEMINI_API_KEY` → `GEMINI_API_KEY` → `GEMINI_API_KEY_FROM_VAULT_NOTE` 순서. 키가 있으면 작업 폴더(`gemini_work/.gemini/settings.json`)에서만 API 키 방식을 쓰고, 전역 Gemini 설정·확장은 건드리지 않는다(`-e none` 로 확장 끔). 키가 없으면 그 PC 의 구글 로그인을 쓴다.
- 기본 모델 `gemini-3.8-flash` (무료 키는 pro 모델 한도가 0).
- 데이터 폴더 `내 문서\my-skills-data\util-notebooklm\`: `notebooks.json`, `answers/`, `pages/`, `sources/`, `notes/`.

## 주의

- **학생·학부모 개인정보가 든 문서는 Gemini·NotebookLM 에 넣지 않는다**(구글 서버로 감).
- 지도서·교재는 저작물이다. 노트북을 공개 공유하지 않는다.
- Gemini 의 인용은 맞는 경우가 많지만(2026-11-22 시험 3/3 정확) 판단에 쓰기 전에 잘라 낸 원문 쪽으로 확인한다.
- NotebookLM 은 공개 API 가 없어 업로드·받아오기는 사람이 한다.

## 문서
- [ISSUES.md](ISSUES.md) — 문제·해결 기록, 할 일
