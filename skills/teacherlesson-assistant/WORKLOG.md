# 작업 기록 (운영 정보)

> 문제·해결 기록은 [ISSUES.md](ISSUES.md)에 한곳으로 모았다(2026-11-25 정리). 이 파일에는 날짜별 요약과 링크, 그리고 운영 정보(수업 흐름이 만들어지는 순서)만 둔다.

## 수업 흐름이 만들어지는 순서 (운영 정보)

1. `notebook_sources.py`가 지도서 PDF에서 글자를 뽑아 `notebooklm/<과목>/<단원>.md`에 차시별 구간을 만든다.
2. `prepare_lessons.py`는 해당 차시 구간을 우선 가져와 Gemini CLI로 수업흐름 JSON을 만든다. 구간이 없으면 Supabase 차시의 PDF 경로에서 쪽을 발췌한다.
3. 결과는 `flows/<lesson_id>.json`에 저장하고 수업 비서가 읽는다.

NotebookLM 단추는 과목 노트북을 열고 질문을 준비하는 별도 기능이다. 자동 수업 준비 단추는 NotebookLM에 직접 질문하지 않고, NotebookLM에 올릴 때 쓰는 같은 `.md` 소스를 Gemini에 전달한다.

## 2026-11-23 — 2학기 진도와 수업 준비

- Supabase를 진도 원본으로 전환(2학기 91건 대조·이관) → [ISSUE-024](ISSUES.md)
- 수업 흐름 생성: 11월 23일 수학 6단원 4차시·도덕 7단원 2차시(각 4단계), 11월 24일 국어·수학·미술 4차시(3~5단계) → [ISSUE-016](ISSUES.md)
- 고친 문제 → [ISSUE-026](ISSUES.md)(옛 `pdf_splits` 경로), [ISSUE-027](ISSUES.md)(차시 선택 목록 잘림), [ISSUE-028](ISSUES.md)(같은 교시 완료 수업이 여러 개), [ISSUE-029](ISSUES.md)(실제로 할 차시 고르기가 날짜를 무시)

## 2026-11-24 — 국어 매체 단원, 미술 사이트, 화면·속도

- 국어 3.5 매체 단원 `실천하기` 연결(번호 누락 보정, 5차시 `lesson-0410` 흐름 재생성) → [ISSUE-025](ISSUES.md)
- 미술3 아트앤컬쳐 e-book 경로 확인(5·6교시 활동 2, 56~57쪽)과 도우미 구현 대기 → [ISSUE-006](ISSUES.md)
- 단계 시간 ±1분·늦음 안내·단계 flag → [ISSUE-013](ISSUES.md), 진도 조정 속도 → [ISSUE-022](ISSUES.md), NotebookLM 창 앞으로 가져오기 → [ISSUE-002](ISSUES.md)
