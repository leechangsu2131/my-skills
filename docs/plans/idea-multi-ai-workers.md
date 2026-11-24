# 아이디어: 여러 AI 작업자에게 일 나눠 맡기기

> 상태: **아이디어 (아직 실행 안 함)** · 적은 날: 2026-11-25 · 출처: 교사와 Claude Code 대화
> 실행하기로 하면 아래 "준비할 것" 두 가지부터 만든다.

## 쓸 수 있는 작업자

| 도구 | 수 · 갱신 | 성격 |
|---|---|---|
| Claude Code (교사 PC) | Pro 하나, 사용량이 귀함 | 비밀값(.env)·지도서 PDF·크롬 사이트 로그인이 있는 유일한 곳 |
| 웹 Claude 작업자 | 3~4명 | 저장소만 봄. 키·지도서·로그인 없음 |
| bizcoder CLI | 3명, **한 달마다 사용량 갱신** | 중간 크기 코딩(기능 하나 + 시험) |
| Gemini CLI | **많이 구할 수 있음**, 무료 | 양은 많고 판단은 적은 일, 긴 글 읽기 |

## 도구별로 맡길 일

- **Claude Code**: 설계, 실제 연결·통합(슈파베이스·사이트·실제 실행), 다른 작업자 PR 검토·합치기, 판단이 어려운 일
- **웹 Claude · bizcoder**: 키 없이 가짜 자료로 시험할 수 있는 "기능 하나 + 시험" 단위. 예(2026-11-25 정리한 4가지):
  1. 학교 PC 점검 도구 — `teacherlesson-assistant/check_setup.py` + bat (설치·키 이름·데이터 폴더·포트 확인, 값은 출력 안 함)
  2. 자동 시험 보강 — `util-notebooklm/nlm.py`, `prepare_lessons.py`, `auto_split.py` 의 순수 함수 (소스는 안 고치고 tests/ 만, 버그는 ISSUES 에 기록·xfail)
  3. 수업 비서 문서 정리 — ISSUES.md 를 표준 양식(🔵/📌/🟢, ISSUE-번호)으로, WORKLOG 겹침 정리, SKILL·README 를 지금 코드에 맞게
  4. 수업 메모 슈파베이스 동기화 부품 — `memo_sync.py` + `sql/lesson_memos.sql` + 가짜 HTTP 시험 (화면·서버 연결은 교사 PC 에서 Claude Code 가)
- **Gemini CLI** (반복·대량):
  1. 스킬 58개 SKILL.md·ISSUES.md 양식·쉬운 한국어 점검 (스킬 하나씩)
  2. 시험 없는 스킬에 작은 함수 시험 쓰기 (스킬 하나에 한 명)
  3. (교사 PC) 🌙 자동 준비로 만든 `flows/*.json` 을 지도서 글(md)과 대조해 다른 차시 내용·지어낸 내용 표시
  4. (교사 PC) 한 주 수업 메모에서 출판사별 반복되는 특징 후보 뽑기 → 교사가 골라 `publisher_notes.json` 에
  5. (교사 PC) `teacherlesson-guide/auto_split.py` 를 단원마다 돌리고 검사 실패 단원 목록 만들기

## 준비할 것 (실행하기로 하면)

1. **작업 목록 `docs/TASKS.md`** — 일마다: 번호 · 맞는 도구(Claude/bizcoder/웹 Claude/Gemini) · 고쳐도 되는 파일 · 끝난 기준 · 시험 명령 · 맡은 사람·브랜치. 작업자는 여기서 골라 가고 PR 로 올림. bizcoder 는 한 달 사용량이 새로 생기면 다음 일을 이어받음
2. **도구별 규칙 파일 `GEMINI.md`·`AGENTS.md`** (저장소 루트) — `CLAUDE.md`·`CONTRIBUTING.md` 규칙을 가리키는 짧은 파일: 개인정보·비밀값 금지, `git add -A` 금지, 브랜치+PR, `python tools/build_catalog.py --check`. 교사 PC 의 Gemini 에는 다른 확장(bkit)이 붙어 있어 저장소 규칙 파일이 있어야 섞이지 않음

## 주의

- 여럿이 `main` 에 바로 올리면 부딪힘 → 작업자는 **브랜치 + PR**, 합치기는 Claude Code(또는 교사)
- 같은 파일을 두 작업자에게 주지 않기 (작업 목록에 "고쳐도 되는 파일"을 적는 이유)
- 학생 개인정보·녹음·비밀값이 필요한 일은 교사 PC 밖으로 내보내지 않기
