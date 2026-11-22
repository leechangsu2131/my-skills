# school-todo-kakao 이슈 로그

> 이 스킬에서 생긴 문제와 해결 과정, 진행 중인 일, 할 일을 기록한다.
> 새 항목은 해당 절의 맨 위에 추가하고, 해결되면 '🟢 해결됨'으로 옮긴다. 양식은 맨 아래 주석 참고.

## 🔵 진행 중

### ISSUE-006: 가족·친한 동료 '친구에게 보내기' 등록 간소화 (2026-11-20)
- **상태**: 🔵 진행 중
- **배경**: 받는 사람마다 앱 멤버 등록·카카오 로그인 동의·uuid 복사·GitHub Secret 수정이 필요해 번거로움.
- **조치**: 등록 링크(웹앱 `?join=`) + 챗봇이 동의 후 토큰 교환으로 앱 연결 + `받는사람` 탭 + 아침 실행이 uuid 자동 채움. 친구에게는 사람당 하루 한 통(개인 할 일 제외) + `자세히 보기` 읽기 전용 페이지(`?view=`, `공유링크` 탭). reviewer 검토 반영: 친구 단계 오류가 내 메시지를 막지 않게 분리, 같은 날 중복 발송 방지, 카카오ID 텍스트 저장. 시험: pytest 60, 챗봇 52 통과. 챗봇 v5 배포.
- **추가(2026-11-22)**: 웹앱 주소만 열면 등록 버튼 안내 화면(매일 / 주 1회 출장)이 뜨도록 변경(받는 사람이 주소를 고칠 필요 없음). 챗봇 시험 54개 통과. 배포 전(clasp push·deploy 필요). 카카오 새 콘솔에서는 리다이렉트 URI·클라이언트 시크릿이 `앱 > 플랫폼 키 > REST API 키`, 웹 도메인이 `JavaScript 키 > JavaScript SDK 도메인`에 있다.
- **남은 일**: Apps Script `권한승인` 실행(외부 호출 권한), 카카오 앱에 리다이렉트 URI·Web 도메인(`https://script.google.com`) 등록·친구목록 동의항목 확인, 실제 한 명 등록해 아침 발송 확인. 알려진 한계는 `AGENTS.md` 12-2.
- **관련 파일**: `chatbot/kakao_chatbot.gs`, `schooltodo/recipients.py`, `schooltodo/cli.py`, `schooltodo/db.py`, `schooltodo/kakao.py`

### ISSUE-002: 챗봇·카카오 실제 연결 확인 (2026-11-20)
- **상태**: 🔵 진행 중
- **증상**: 오픈빌더 봇 테스트에서 `[THRUST] skill exec error`. Apps Script 웹앱 주소로 `curl.exe -i -X POST` 하면 첫 줄이 `HTTP/1.1 302 Found`.
- **원인(가설, 미확정)**: Apps Script 웹앱은 POST 응답을 다른 주소로 302 이동시키는데 카카오 스킬 호출은 이동을 따라가지 못한다.
- **해결/조치**: 2026-11-20 중계기 `chatbot/cloudflare_worker.js`(시험 `test_worker.mjs` 10개 통과)를 추가했다. 다음 순서로 확인한다. ① `curl.exe -i -L`로 Apps Script 자체 응답 확인 ② 워커 배포 후 스킬 URL을 워커 주소로 교체 ③ 봇 테스트 `할일`. 자세한 단계는 `AGENTS.md` 5-B, 6절.
- **진행(2026-11-20)**: 302를 따라가면(`curl -L`, `-X POST` 없이) Apps Script가 정상 JSON을 2~3초에 돌려줌 → 가설 확인. 워커 `school-relay`(workers.dev) 배포, 직접 호출 시험 통과(GET 200, 잘못된 키 403, `내아이디`·`할일` 200, 2.9~3.6초). 오픈빌더 스킬 URL을 워커 주소로 교체한 뒤 스킬 테스트·봇 테스트에서 정상 응답("아직 등록되지 않은 사용자예요") 확인 → `skill exec error` 해결. 운영 채널(검색 비허용이라 URL/QR로 추가) 연결·배포 후 휴대폰 카카오톡에서 정상 응답 확인. 챗봇 v2.1(미등록 사용자에게 아이디 안내)을 clasp로 배포, 교사 관리자 등록 후 `할일`·`오늘` 정상(3.2~3.4초). 주의: 윈도우 `curl.exe`에 한글을 `-d`로 직접 넣으면 cp949로 깨지므로 UTF-8 파일(`--data-binary @파일`)로 시험한다.
- **남은 확인**: 실제 카카오 경유 시 5초 안에 응답하는지(직접 호출 3.6초로 여유가 적음), 사용자별 `user.id`, 친구 메시지·`friends` 명령 실제 호출
- **관련 파일**: `chatbot/`, `schooltodo/kakao.py`

## 📌 백로그

### ISSUE-003: 할 일을 안 한 사람에게만 이메일 알림 (2026-11-20)
- **상태**: 📌 백로그
- Apps Script `MailApp`으로 `담당` 가운데 완료기록에 없는 사람에게만 보낸다(무료). 일일 발송 한도를 확인한다. 이어서 아침 카톡에 `완료 3/5` 같은 현황 요약을 넣는다.

### ISSUE-004: 남아 있는 중복 파일 정리 (2026-11-20)
- **상태**: 📌 백로그
- 루트의 `message.py`와 `schooltodo/test_core.py`는 옛 사본이다. 실제 코드는 `schooltodo/message.py`, 시험은 `tests/test_core.py`. 확인 후 삭제한다.

## 🟢 해결됨

### ISSUE-005: 윈도우에서 `morning --dry-run`이 이모지 때문에 멈춤 (2026-11-20)
- **상태**: 🟢 해결 (2026-11-20)
- **증상**: `UnicodeEncodeError: 'cp949' codec can't encode character '\U0001f4c5'`
- **원인**: 윈도우 콘솔 기본 문자 코드(cp949)는 이모지를 출력하지 못한다.
- **해결/조치**: `cli.py`의 `main()`에서 표준 출력을 UTF-8로 바꿨다(GitHub Actions에는 영향 없음).
- **관련 파일**: `schooltodo/cli.py`

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
