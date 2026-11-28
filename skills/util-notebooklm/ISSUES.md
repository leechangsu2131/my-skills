# util-notebooklm 이슈 로그

> 이 스킬에서 생긴 문제와 해결 과정, 진행 중인 일, 할 일을 기록한다.
> 새 항목은 해당 절의 맨 위에 추가하고, 해결되면 '🟢 해결됨'으로 옮긴다.

## 🔵 진행 중

### ISSUE-003: 실제 NotebookLM 노트북으로 찾기 질문 시험 (2026-11-22)
- **상태**: 🔵 진행 중
- **할 일**: 수업 과목 노트북을 만들어 `nb add 수업-수학 <주소>` 로 등록하고, `nb open … --q` 질문으로 원문·쪽 인용이 잘 오는지, 북마클릿 md 가 `split` 으로 잘 잘리는지 확인

## 📌 백로그

### ISSUE-004: 수업 밖 쓰임새 넓히기 (2026-11-22)
- 공문·규정집(admin-edufine 처리 흐름), 투자 보고서(personal-invest-sheet, 비공개 저장소) 등에서 "통째로 읽기 전에 find" 를 쓰도록 각 스킬 문서에 한 줄 연결
- 여러 PDF 를 한 번에 찾기(`find` 에 파일 여러 개) — 아직. ~~답의 `[p.N]` 을 원문과 자동 대조하는 검사~~ → 🟢 `nlm.py verify <pdf> <답.md>` (2026-11-28, S8: 인용문을 쪽 원문과 글자만 남겨 비교, 다른 쪽에 있으면 실제 쪽을 알려 줌, 지어낸 인용은 종료 코드 1. 시험 `tests/test_verify.py`. 실제 PDF·Gemini 답으로는 아직 안 돌려 봄 → 교사 PC 에서 `find` 뒤에 한 번 돌려 보기)

### ISSUE-005: Gemini 무료 한도 (2026-11-22)
- 무료 키는 `gemini-3.1-pro` 한도 0, `gemini-2.5-flash` 는 새 사용자 사용 불가 → 기본 `gemini-3.8-flash`. 모델 이름이 바뀌면 `DEFAULT_MODEL` 을 고친다.

## 🟢 해결됨

### ISSUE-002: gemini.cmd 가 여러 줄 질문을 첫 줄만 넘김 (2026-11-22)
- **상태**: 🟢 해결 (2026-11-22)
- **증상**: `find` 의 답이 "찾을 내용을 입력해 주세요" — 질문 규칙이 전달되지 않음
- **원인**: 윈도우에서 `gemini.cmd` 는 cmd.exe 를 거치며 인자를 줄바꿈에서 자름(& % 따옴표도 위험)
- **해결/조치**: `node <npm>/node_modules/@google/gemini-cli/bundle/gemini.js` 를 직접 실행(`gemini_command`)
- **관련 파일**: `nlm.py`

### ISSUE-001: Gemini CLI 가 로그인 창을 띄우거나 이 PC 확장 글이 답에 섞임 (2026-11-22)
- **상태**: 🟢 해결 (2026-11-22)
- **증상**: 전역 설정이 `oauth-personal` 이라 키를 줘도 "Opening authentication page"; bkit 확장 안내문이 답에 섞임
- **해결/조치**: 작업 폴더에만 `.gemini/settings.json`(`gemini-api-key`)을 두고 `-e none` 으로 확장을 끔. 전역 설정은 그대로
- **관련 파일**: `nlm.py` (`gemini_find`)
