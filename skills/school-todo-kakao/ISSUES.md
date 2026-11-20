# school-todo-kakao 이슈 로그

> 이 스킬에서 생긴 문제와 해결 과정, 진행 중인 일, 할 일을 기록한다.
> 새 항목은 해당 절의 맨 위에 추가하고, 해결되면 '🟢 해결됨'으로 옮긴다. 양식은 맨 아래 주석 참고.

## 🔵 진행 중

### ISSUE-002: 챗봇·카카오 실제 연결 확인 (2026-11-20)
- **상태**: 🔵 진행 중
- **증상**: 챗봇(`chatbot/kakao_chatbot.gs`)은 가짜 환경 시험(`node chatbot/harness2.js`, 38개 통과)만 했다. 친구에게 보내기와 `friends` 명령도 실제로 호출해 보지 않았다.
- **확인할 것**: Apps Script 웹앱이 오픈빌더 스킬 서버로 동작하는지(리다이렉트 처리), 5초 안에 응답하는지, 친구 메시지를 받는 사람의 동의·팀원 등록 조건
- **관련 파일**: `chatbot/`, `schooltodo/kakao.py`

## 📌 백로그

### ISSUE-003: 할 일을 안 한 사람에게만 이메일 알림 (2026-11-20)
- **상태**: 📌 백로그
- Apps Script `MailApp`으로 `담당` 가운데 완료기록에 없는 사람에게만 보낸다(무료). 일일 발송 한도를 확인한다. 이어서 아침 카톡에 `완료 3/5` 같은 현황 요약을 넣는다.

### ISSUE-004: 남아 있는 중복 파일 정리 (2026-11-20)
- **상태**: 📌 백로그
- 루트의 `message.py`와 `schooltodo/test_core.py`는 옛 사본이다. 실제 코드는 `schooltodo/message.py`, 시험은 `tests/test_core.py`. 확인 후 삭제한다.

## 🟢 해결됨

### ISSUE-001: Claude 대화 인수인계본 반영 (2026-11-20)
- **상태**: 🟢 해결 (2026-11-20)
- **내용**: 주말 메시지, `TASK_DAY`·`TASK_IMMINENT_DAYS` 설정, 카카오 챗봇 v2(`chatbot/`)를 반영했다. 규칙과 배경은 `AGENTS.md`에 있다.
- **검증**: 앞 대화에서 돌리지 못한 pytest 전체를 실행해 46개가 통과했고, 챗봇 시험도 38개가 통과했다.
- **관련 파일**: `schooltodo/cli.py`, `schooltodo/message.py`, `tests/test_core.py`, `.github/workflows/morning.yml`, `chatbot/`

<!--
항목 양식 (복사해서 사용)

### ISSUE-001: 한 줄 제목 (YYYY-MM-DD)
- **상태**: 🔵 진행 중 | 📌 백로그 | 🟢 해결 (YYYY-MM-DD)
- **증상**: 무엇이 어떻게 안 됐나 (오류 메시지 그대로)
- **원인**: 확인된 원인
- **해결/조치**: 무엇을 바꿨나, 재발 방지
- **관련 파일**: `script.py`, 커밋 해시
-->
