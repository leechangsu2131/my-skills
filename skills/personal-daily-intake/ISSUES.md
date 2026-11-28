# personal-daily-intake 이슈 로그

> 이 스킬에서 생긴 문제와 해결 과정, 진행 중인 일, 할 일을 기록한다.
> 새 항목은 해당 절의 맨 위에 추가하고, 해결되면 '🟢 해결됨'으로 옮긴다.

## 🔵 진행 중

### ISSUE-005: 제미나이 내보내기 북마클릿 — 실제 화면 확인 (2026-11-28)
- **상태**: 🔵 진행 중
- **된 것**: `gemini_bookmarklet.js` — 대화 화면의 `user-query`·`model-response` 요소에서 내가 쓴 말·답을 JSON 으로, 마지막 답의 코드 상자가 `--- date:` 로 시작하면 `하루기록-날짜.md` 로 내려받음. `intake.py` 가 다운로드 폴더에서 옮김(`collect_downloads`). 가짜 화면(node)으로 두 파일이 나오는 것 확인.
- **확인 필요**: 실제 gemini.google.com 화면의 요소 이름(바뀌면 "Gemini 대화를 못 찾았어요" 알림), 코드 상자 글에 '복사' 같은 단추 글자가 섞이는지, 긴 대화에서 위쪽이 안 불러와진 경우, 다운로드 폴더를 옮긴 PC(`.env` `PERSONAL_DAILY_INTAKE__DOWNLOADS`).
- **많이 한꺼번에**: 지난 대화 전체는 Google 테이크아웃(내 활동 → Gemini 앱)으로 받는 길도 있음 — 필요하면 그 형식 읽기를 붙임.

### ISSUE-002: 실제 제미나이 정리본으로 첫 시험 (2026-11-27)
- **상태**: 🔵 진행 중
- **할 일**: 교사가 제미나이 스킬로 하루 이틀 말해 본 md 로 `plan` → `apply`. 갈래가 자주 틀리거나 `- 키: 값` 형식이 흔들리면 gem_prompt.md 를 고친다.
- **확인할 것**: 일정DB 시트 실제 쓰기(서비스 계정), Notion 독서 DB 새 행, 볼트 daily 노트가 Obsidian 에서 잘 보이는지.

## 📌 백로그

### ISSUE-004: 제미나이 없이 PC 에서 말하기 → md (2026-11-28)
- **상태**: 📌 백로그
- 참고: 예람쌤 RamBot·RamNeis 사용 가이드(교사 개인 드라이브 `my-skills-개인자료\resource\guide-rambot.pdf`·`guide-ramneis.pdf`, 2026-11-28 읽음). 기능 생각만 가져오고 글·그림·코드는 베끼지 않는다.
- PC 마이크로 말하기 → 내 PC 받아쓰기(faster-whisper, 수업 비서 `transcribe.py` 와 같은 엔진, 고쳐 쓰기 사전 함께 — 수업 비서 ISSUE-053 ①) → Claude Code 또는 Gemini CLI 가 `gem_prompt.md` 지침대로 md → inbox. 제미나이 스킬이 없어져도 같은 흐름이 됨.

### ISSUE-001: Notion 업무일지·일기·습관기록 DB에 쓰기 (2026-11-27)
- **상태**: 📌 백로그
- **증상**: 지금 중앙 .env 의 Notion 연결(`NOTION_TOKEN`)은 독서 DB·도서 신청 DB만, `NOTION_API_KEY` 는 수업실행·진도·학생 기록 DB만 보인다. 업무일지·일기·습관기록은 어느 쪽에도 공유돼 있지 않다.
- **필요한 것**: 교사가 Notion 에서 그 DB 페이지 → ··· → 연결 → **`book manage`**(`NOTION_TOKEN` 의 연결 이름) 추가. 확인은 `python intake.py notion`(2026-11-28 추가). 그 뒤 속성을 읽어 갈래별 쓰기를 붙인다.
- **함께 볼 것**: 수업 조각을 Notion 수업실행 `메모`(그날·과목 행)에 덧붙이기 — 기존 행을 고치는 일이라 표로 확인받는 방식으로. 진도는 이제 Supabase(teacherlesson-schedule)가 원본이라 수업실행이 아직 쓰이는지 먼저 확인.

### ISSUE-003: 후보를 바로 반영하는 길 (2026-11-27)
- **상태**: 📌 백로그
- 수업 요령 → 과목 노트 '진행 방식', 학생 → 학생 기록 DB(이름 관계 찾기), 투자 → 투자시트 분위기 일지. 지금은 '후보'로 daily 에 남기고 교사가 고르면 손으로 한다.

## 🟢 해결됨

_없음_
