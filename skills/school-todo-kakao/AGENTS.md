# school-todo-kakao — 에이전트 작업 안내

> 목표·결정·현재 상태·해야 할 일을 모은 문서. 처음 내용은 2026-11-18 Claude 대화 인수인계(HANDOFF.md)에서 왔고, 이후 변경은 여기에 바로 고친다.
> 작업 방식: 코드로 할 수 있는 것은 직접 하고 시험 결과를 보여 준다. 사람이 화면에서 눌러야 하는 단계는 6절을 보고 화면 이름과 함께 한 단계씩 안내한다. 막히면 추측하지 말고 어느 화면·어떤 오류였는지 묻는다.
> 문제·해결 기록은 `ISSUES.md`, 사람용 설명은 `README.md`.

## 1. 목표와 사용자
- 사용자는 초등학교 교사 한 명(3학년 담임 + 체육업무). 윈도우 PC를 쓰고 명령은 `명령 프롬프트`와 `curl.exe`로 실행한다. 개발 경험은 많지 않다 → 설명은 메뉴 이름까지 구체적으로.
- 목표 ① 공용 학교 시트의 일정과 본인 할 일을 개인 구글 시트 `일정DB`에 모아 **매일 아침 카카오톡**으로 알려준다(구현·가동 중).
- 목표 ② **카카오톡 챗봇**: 담당자(여러 명)가 챗봇에 "완료 ○○"라고 보내면 **그 사람 몫으로** 완료가 기록되고, 교사는 누가 했고 누가 안 했는지 본다. 안 한 사람에게만 알림(이메일)이 가게 한다. ← **지금 만드는 중, 연결 단계에서 막힘.**
- 사용자가 직접 하는 방법도 병행한다: ⓐ 시트 상태 칸에 ✔ 입력, ⓑ Claude 대화창에서 "일정DB에서 ○○ 완료 처리해줘".

## 2. 절대 원칙 (결정 이력 포함)
1. **무료만.** 챗봇 Event API(챗봇이 먼저 보내기)는 건당 15원·월렛·비즈니스 인증이 필요해서 **쓰지 않기로 결정**. 챗봇이 먼저 말 거는 기능이 필요한 알림은 **이메일**(무료)로 한다.
2. 비밀값은 저장소에 커밋하지 않는다(깃허브 Secrets, Apps Script 속성, Cloudflare Secret, 시트에만).
3. 학생·학부모 개인정보를 일정 내용에 넣지 않는다(카카오 서버·로그를 거침).
4. 기존 파일의 줄바꿈 CRLF를 유지한다.
5. 규칙을 바꾸면 시트의 `안내` 탭과 이 문서(`AGENTS.md`)를 같이 고친다.
6. 사람이 지운 행·결정을 임의로 되살리지 않는다(되살리기 전에 확인).

## 3. 전체 구조
```
공용 학교 시트 ─(sync)─▶ 일정DB(개인 구글 시트) ─(morning)─▶ 카카오톡 "나에게 보내기"
빠른입력 탭 ──(sync가 정식 행으로)──┘                     └▶ (선택) 친구 몇 명에게 "출장" 주간 메시지
cron-job.org ─POST─▶ GitHub Actions(morning.yml, workflow_dispatch) ─▶ python -m schooltodo sync / morning

[챗봇] 카카오톡 채널 ─▶ 오픈빌더 폴백 블록(스킬) ─POST─▶ (Cloudflare Worker 중계) ─▶ Apps Script 웹앱 ─▶ 일정DB·구성원·완료기록 탭
```
- 깃허브 `schedule`(cron)은 몇 시간씩 늦거나 누락돼 **제거**했다. 실행 시각은 **cron-job.org가 매일**(주말 행사 때문에) 호출, 시간대 Asia/Seoul.
  호출: `POST https://api.github.com/repos/<소유자>/my-skills/actions/workflows/morning.yml/dispatches`, 헤더 `Authorization: Bearer <fine-grained PAT, Actions read/write>`, `Accept: application/vnd.github+json`, 본문 `{"ref":"main"}`. 응답 204가 성공(시험 완료, 아침 카톡 정상 수신 확인됨).
- 저장소 이름 `my-skills`, 이 프로젝트는 하위 폴더 `skills/school-todo-kakao/`.
- 카카오 계정: 채널·챗봇은 "메시지를 보내는 본 계정"으로 만들기를 권했고, 교사의 다른(부) 계정은 챗봇 `구성원` 탭에서 `관리자`로 등록해 전체 권한을 준다.

## 4. 파일 (저장소 `skills/school-todo-kakao/` 기준)
| 경로 | 역할 | 상태 |
|---|---|---|
| `.github/workflows/morning.yml` | 아침 실행 워크플로(수동 실행 전용으로 변경) | 가동 중 |
| `skills/school-todo-kakao/schooltodo/message.py` | 아침 메시지 조립(주말·지연·할 일·그 주 일정·주간 출장) | 시험 통과 |
| `.../schooltodo/cli.py` | `sync`, `morning`, `friends` 명령 | 시험 통과(dry-run) |
| `.../schooltodo/kakao.py` | 토큰 갱신, 나에게/친구에게 보내기, `list_friends` | 일부 미시험 |
| `.../schooltodo/{sync,inbox,classify,db,dates,sources,envload}.py` | 동기화·빠른입력·분류·시트/CSV 입출력 | 기존 |
| `.../tests/` | pytest 시험(+ fixtures, 모두 가상 데이터) | 46개 통과(2026-11-20) |
| `.../chatbot/kakao_chatbot.gs` | **챗봇 서버(Apps Script 웹앱) v2** | 가짜 시트로 38개 통과(2026-11-20 재확인), 실제 연결 미완 |
| `.../chatbot/harness2.js` | 위 챗봇의 가짜 시트 시험(`node harness2.js`) | |
| `.../chatbot/cloudflare_worker.js` | **중계기**(구글의 302 이동을 대신 따라감) | 가짜 서버로 10개 통과(2026-11-20 재확인), 배포 전 |
| `.../chatbot/test_worker.mjs` | 중계기 시험(`node test_worker.mjs`) | |
| `.../chatbot/kakao_chatbot_setup.md` | 사람용 설치 순서 | |
| `.../README.md`, `.env.example`, `config.example.toml` 등 | 기존 프로젝트 문서·설정 예시 | |

`cli.py`는 `message.py`·`kakao.py`의 새 함수를 불러오므로 **세 파일은 항상 함께** 바꾼다.

## 5. 해야 할 일 (우선순위 순)
### A. 로컬 검증 — 완료 (2026-11-20)
- `pytest -q` 46개 통과, `node harness2.js` 38개, `node test_worker.mjs` 10개 통과.
- `morning --dry-run` 미리보기 정상. 윈도우 콘솔(cp949)에서 이모지 때문에 멈추던 문제는 `cli.py`가 UTF-8로 출력하도록 고쳤다.

### B. 챗봇 연결 막힘 해결 (현재 최우선)
- 증상: 오픈빌더 **봇 테스트**에서 `[THRUST] skill exec error`. 사용자가 Apps Script 웹앱 주소에 `curl.exe -i -X POST "웹앱URL?key=SECRET" ...`를 보냈더니 첫 줄이 **`HTTP/1.1 302 Found`**.
- 가설(미확정): Apps Script 웹앱은 POST 응답을 다른 주소로 302 이동시키는데 카카오 스킬 호출이 이를 따라가지 못한다. 근거는 증상 일치뿐이고 확정 증거는 없다.
- 해결 경로: ① 사용자가 `curl.exe -i -L ...`로 Apps Script 자체가 맞게 답하는지 확인(`선생님의 챗봇 아이디예요: test`가 보여야 함) ② `chatbot/cloudflare_worker.js`를 무료 Cloudflare Workers에 배포하고 카카오 스킬 URL을 워커 주소(`?key=KAKAO_KEY`)로 변경 ③ 봇 테스트에서 `할일` → "아직 등록되지 않은 사용자예요"가 나오면 연결 성공.
- 이것도 안 되면: 응답 5초 제한(콜백 옵션 검토), 응답 JSON 형식(`answer_json_format` 문서), 스킬 URL의 `?key=` 불일치, 폴백 블록에 스킬이 실제로 연결·저장됐는지를 순서대로 점검. 대안 호스트(Cloudflare Workers에서 구글 시트 API를 직접 호출하도록 챗봇 로직 이전)도 검토 가능하나 구글 서비스 계정 설정이 필요해 복잡하다.
- 참고: 봇 테스트의 오류는 오픈빌더 "스킬 오류 내역"에 **나오지 않는다**(운영 채널 오류만 표시).

### C. 챗봇 기능 완성·검증
- 실제 카카오 요청에서 `userRequest.user.id`가 사용자마다 다른지, 응답이 5초 안에 오는지 확인.
- `구성원` 탭에 담당자를 등록하는 절차(챗봇에 `내아이디` → 시트에 붙여 넣기)를 시험.
- 필요하면 자기 등록 기능(예: 일회용 코드)을 검토. 단, 이름만으로 자기 등록을 허용하면 사칭 위험이 있다.

### D. 안 한 사람에게 이메일 알림 (무료, 아직 미구현)
- Apps Script `MailApp`으로 `담당`에 포함되고 `완료기록`에 없는 사람의 `구성원` 이메일로 발송. 메일 끝에 "챗봇에서 `완료 ○○`라고 보내세요" 안내. 일일 발송 한도는 구글 문서에서 확인(개인 계정은 수십~수백 통대로 알고 있음 — 확인 필요). 트리거는 시간 기반(예: 평일 아침).

### E. 아침 카톡에 현황 요약 (미구현)
- 파이썬 `morning`이 `완료기록`을 읽어 "완료 3/5, 안 한 사람: …"를 교사에게 한 줄 요약으로 추가.

### F. 선택
- 빠른입력 탭에 `완료 ○○` 명령, 읽기 전용 권한 같은 세분화, `morning.yml`의 동작하지 않는 guard 단계 정리.

## 6. 사람이 직접 해야 하는 일 (화면 이름은 2026-11 기준, 일부는 기억에 의존 — 다르면 캡처 요청)
### 6-1. 구글 시트 / Apps Script
1. `일정DB` 시트 → 상단 `확장 프로그램` → `Apps Script` → 기존 코드 삭제 후 `chatbot/kakao_chatbot.gs` 붙여 넣고 저장.
2. 왼쪽 톱니바퀴 `프로젝트 설정` → `스크립트 속성` → `SECRET`(20자 이상 영문·숫자) 추가. 처음 관리자 등록용 `ALLOWED_IDS`는 챗봇 아이디를 알게 된 뒤 추가.
3. 오른쪽 위 `배포` → `새 배포` → 유형 `웹 앱` → 실행 사용자 `나`, 액세스 `모든 사용자` → 배포(권한 승인; "확인되지 않은 앱"이면 `고급` → `이동` → `허용`). 코드를 고칠 때마다 `배포 관리 → 새 버전`.
4. 웹 앱 URL(`…/exec`)을 브라우저로 열어 "켜져 있어요"가 나오는지 확인. **주소는 `/exec`로 끝나야 한다(`/dev`는 401).**
### 6-2. Cloudflare (중계)
cloudflare.com 무료 가입 → `Workers & Pages` → `Create` → `Hello World` → 이름 → `Deploy` → `Edit code`에 `cloudflare_worker.js` 붙여 넣고 `Deploy` → `Settings` → `Variables and Secrets`에 `KAKAO_KEY`(새 비밀값), `APPS_SCRIPT_URL`(웹 앱 URL, `?key=` 제외), `APPS_KEY`(= Apps Script의 SECRET) → 워커 주소로 `curl.exe -i -X POST "워커주소?key=KAKAO_KEY" -H "Content-Type: application/json" -d "{\"userRequest\":{\"utterance\":\"내아이디\",\"user\":{\"id\":\"test\"}}}"` 시험(기대 200 + JSON).
### 6-3. 카카오
1. 카카오톡 채널 관리자센터(center-pf.kakao.com)에서 채널 만들기(프로필 비공개·검색 허용 끔).
2. 카카오비즈니스(business.kakao.com) 로그인 → `채널` → `챗봇` → (처음이면 챗봇 관리자센터 가입) → `봇 만들기` → 유형 `카카오톡 챗봇` → 이름 입력.
3. `스킬` → `스킬 목록` → `생성` → URL에 **워커주소?key=KAKAO_KEY**(중계를 쓰는 경우) 또는 `웹앱URL?key=SECRET` 입력.
4. `시나리오` → 기본 블록 `폴백 블록` → `파라미터 설정`에서 스킬 선택 → 봇 응답을 `스킬데이터 사용`(이름은 기억 기준)으로 설정.
5. `봇 테스트`(우측 메뉴 또는 Ctrl+E)에서 `할일` 시험.
6. 봇 관리 탭 `카카오톡 채널 연결` → `운영 채널 선택하기` → 채널 선택 → `배포`(`배포 히스토리`에서 상태 확인).
7. 카카오톡에서 채널 추가 후 `내아이디` 전송 → 나온 글자를 Apps Script 속성 `ALLOWED_IDS`와 시트 `구성원` 탭의 교사 줄 `챗봇아이디`에 붙여 넣기. 담당자도 각자 한 번씩 `내아이디`를 보내 교사에게 전달 → `구성원` 탭에 붙여 넣기.
### 6-4. 깃허브 / cron-job.org (이미 설정됨, 변경 시 참고)
- 필요한 Secrets·Variables는 8절. cron-job.org 작업의 **요일은 매일**(월~금만이면 주말 출장 알림이 안 간다).

## 7. 데이터 모델 (구글 시트 `일정DB` 문서)
### 7-1. 탭 `일정DB`
열: `키 | 날짜 | 구분 | 내용 | 상태 | 출처 | 대상 | 담당` (코드는 열 이름으로 읽음: 순서는 바뀌어도 되나 이름은 그대로. `담당`은 선택 열.)
- `키` = `MMDD-` + 내용 앞 10글자(공백 제거). sync가 중복 방지에 쓰고 기존 행은 덮어쓰지 않는다. **완료기록이 키로 연결되므로 키를 고치지 않는다.**
- `날짜` = `yyyy-mm-dd` **텍스트**(열 서식 텍스트. 날짜값과 섞이면 정렬이 어긋난다).
- `구분`: `개인`=기한 있는 해야 할 일 / `출장`·`학교`·`공지`=행사. 빠른입력은 글에 `출장`이 있으면 `출장`, 아니면 `개인`.
- `출처`: `자동`(sync가 공용 시트에서 가져옴) / `수동`. 지연 판단에는 쓰이지 않는다.
- `상태`: `✔`이면 완료(아침 메시지에서 제외). 비어 있어야 알린다.
- `대상`: `타학년·유치원`이면 제외, 그 외(`전체`,`3학년` 등)는 포함.
- `담당`: 이름(쉼표로 여러 명)·그룹 이름·`전체`. 비면 공유 일정이거나 교사 본인의 할 일.
- 정렬 시 **H열(담당)까지** 범위에 넣는다(A~G만 정렬하면 담당이 어긋난다).
- 알려진 문제: 공용 시트에 개교기념식 옛 날짜(11/25)가 남아 있으면 sync가 `1125-개교기념식` 행을 다시 추가한다 → 그 행은 상태 `✔`로 막아 두었다(근본 해결은 공용 시트 날짜 수정).
### 7-2. 탭 `구성원`
`이름 | 그룹 | 챗봇아이디 | 역할(관리자/일반) | 이메일` — 사람 추가는 한 줄. 그룹은 쉼표로 여러 개 가능.
### 7-3. 탭 `완료기록`
`시각 | 키 | 이름 | 내용` — 챗봇이 완료할 때마다 한 줄 추가(없으면 자동 생성). 취소 = 그 사람 줄 삭제. 담당자가 모두 완료하면 일정DB `상태`에 `✔`가 자동 입력된다.
### 7-4. 기타 탭
`빠른입력`(교사가 빠르게 적는 입력), `안내`(규칙·이슈 복구 기록 — 규칙을 바꾸면 같이 갱신).

## 8. 아침 메시지·주간 규칙 (`message.py`)
**평일**: ① `📅 오늘` ② `⚠ 지연`(구분 `개인`·기한 지남·상태 비어 있음, 최대 5건; 행사는 지나가면 그냥 사라짐) ③ `📌 기한 있는 할 일`(구분 `개인`, 30일 이내, 최대 5건; **월요일(TASK_DAY)에 전부, 다른 날은 기한 3일 전(TASK_IMMINENT_DAYS)에 한 번만**; 그 3일 전이 주말이면 금요일에; 오늘·다음 근무일 항목은 제외; `TASK_DAY=daily`면 매일) ④ `👉 다음 근무일 미리보기` ⑤ `🗓 이번 주 남은 일정`(금요일에는 `🗓 주말·다음 주 일정`, 구분 `개인` 아닌 행사만, 최대 6건). 카톡 글자 수 제한으로 여러 통으로 나뉜다.
**주말(토·일)**: 평소 메시지는 보내지 않고, 오늘 행사(출장·학교·공지)가 있을 때만 `📅 오늘` 한 통. 없으면 아무것도 안 보낸다.
**주간 출장 메시지**(가족 등): 구분이 `출장`인 내 행의 향후 7일치를 `WEEKLY_DAY`(기본 월요일)에 `WEEKLY_FRIEND_UUIDS`(최대 5명)에게 친구 메시지로 보낸다.

## 9. 챗봇 설계 (`chatbot/kakao_chatbot.gs`)
- 요청: 오픈빌더가 스킬 URL로 HTTP POST(JSON). 사용자 구분은 `userRequest.user.id`(종류 botUserKey). 응답은 `{version:"2.0", template:{outputs:[{simpleText:{text}}]}}`, 텍스트 900자로 자른다. 처리 제한 시간 5초.
- 인증: URL의 `?key=SECRET`(Apps Script 속성) + `구성원` 탭의 챗봇아이디. `ALLOWED_IDS` 속성은 처음 관리자 등록용(관리자 아이디 목록). 아이디를 모르는 사용자는 `내아이디`만 쓸 수 있다.
- 명령: `완료 ○○`·`○○ 완료`·`나 완료했어`(남은 일이 하나일 때만)·`되돌리기 ○○`·`할일`·`오늘`, 관리자는 `현황 [키워드]`·`완료 ○○ 이름`(대신 처리).
- 권한: 일반 담당자는 **자기 몫만**. 담당이 아닌 일정·남의 몫은 거부. 관리자는 전체. 담당이 비어 있는 행(교사 본인의 할 일)은 관리자만 상태 칸 ✔로 처리.
- 담당 해석: `담당` 칸의 각 항목을 먼저 구성원 이름으로, 없으면 그룹 이름으로, `전체`는 모든 구성원으로. 못 찾은 항목은 `현황`에 경고.
- 동시 처리: 스크립트 잠금(LockService)으로 두 사람이 동시에 완료해도 기록이 꼬이지 않게 한다.
- 키워드가 여러 일정에 맞으면 후보 목록을 보여주고 되묻는다.

## 10. 설정값
- 깃허브 Secrets: `KAKAO_REST_API_KEY`, `KAKAO_CLIENT_SECRET`, `KAKAO_REFRESH_TOKEN`, `KAKAO_FRIEND_UUIDS`, `GOOGLE_SERVICE_ACCOUNT_JSON`, `DB_SHEET_ID`, `SRC_WEEK_SHEET_ID`, `SRC_WEEK_GID`, `SRC_TODAY_SHEET_ID`, `SRC_TODAY_GID`, `MY_NAME`, `GH_PAT`(리프레시 토큰 갱신 저장용), `WEEKLY_FRIEND_UUIDS`
- 깃허브 Variables: `KAKAO_SEND_TO_ME`, `WEEKLY_DAY`(0=월…6=일), `TASK_DAY`, `TASK_IMMINENT_DAYS`
- Apps Script 속성: `SECRET`, `ALLOWED_IDS`
- Cloudflare: `KAKAO_KEY`, `APPS_SCRIPT_URL`, `APPS_KEY`
- cron-job.org: 호출 주소·토큰(깃허브 fine-grained PAT, `Actions: Read and write`, 이 저장소만)

## 11. 카카오 사실 정리 (출처 표기, 확인일 2026-11-18)
- 스킬 서버 개념·형식: 요청·응답 모두 JSON POST — https://kakaobusiness.gitbook.io/main/tool/chatbot/skill_guide/make_skill
- 블록에 스킬 연결(파라미터 설정 → 스킬 선택) — .../skill_guide/apply_skill_to_block
- 응답 JSON 형식 — .../skill_guide/answer_json_format
- 스킬 오류 내역(운영 채널 오류만 표시, 봇 테스트 오류는 확인 불가) — .../skill_guide/check_skill_error_history
- 스킬 처리 5초 제한과 콜백 — .../skill_guide/ai_chatbot_callback_guide
- 봇 테스트(Ctrl+E) — .../main_notions/bot_test
- **Event API(유료): 건당 15원, 월렛 연결, 비즈니스 인증 채널·비즈앱 필요, 채널 친구에게만, 1회 100명, 전체 사용자 목록 조회 불가 — 쓰지 않기로 함** — .../main_notions/event-api
- 챗봇 일반 이용료는 2022년에 무료 전환이 발표됐다(지금도 같은지는 관리자센터 화면에서 확인 필요) — https://www.kakaocorp.com/page/detail/9756
- 메시지 REST API(나에게 보내기/친구에게 보내기): 보내는 사람·받는 사람 모두 앱에 연결·동의(친구목록, 메시지 전송) 필요, 개발 단계는 팀원 계정, 실서비스 적용은 추가 기능 신청과 심사, 친구 발송은 쌍당 하루 20건 제한(카카오 문의 답변 기준), 나에게 보내기는 제한 없음 — https://developers.kakao.com/docs/latest/message/rest-api
- 문서 사이트(`kakaobusiness.gitbook.io/main/tool/chatbot`)는 페이지 URL 뒤에 `.md`를 붙이면 마크다운으로 받을 수 있고 `llms.txt` 목차가 있다. 사용자 화면에서 사이트 검색이 동작하지 않았다.

## 12. 시험 명령 모음
```
# 파이썬 전체
cd skills/school-todo-kakao && pip install -r requirements-dev.txt && pytest -q
# 아침 메시지 미리보기(시트 없이)
python -m schooltodo morning --db-csv tests/fixtures/db.csv --today 2026-11-18 --dry-run
python -m schooltodo morning --db-csv tests/fixtures/db.csv --today 2026-11-23 --dry-run --weekly
# 챗봇·중계기
cd chatbot && node harness2.js && node test_worker.mjs
# 실제 호출(윈도우 명령 프롬프트): 먼저 Apps Script, 다음 워커
curl.exe -i -L -X POST "웹앱URL?key=SECRET" -H "Content-Type: application/json" -d "{\"userRequest\":{\"utterance\":\"내아이디\",\"user\":{\"id\":\"test\"}}}"
curl.exe -i -X POST "워커주소?key=KAKAO_KEY" -H "Content-Type: application/json" -d "{\"userRequest\":{\"utterance\":\"내아이디\",\"user\":{\"id\":\"test\"}}}"
```

## 12-1. 챗봇 코드 배포 (clasp, 2026-11-20부터)
- Apps Script는 시트에 묶인 프로젝트라 `clasp list`에 안 나온다. 작업 폴더는 저장소 밖 `내 문서\my-skills-data\school-todo-kakao\apps_script\`(`.clasp.json`에 스크립트 ID, `Code.js`, `appsscript.json`). 로그인 계정은 시트 주인 구글 계정.
- 순서: 저장소 `chatbot/kakao_chatbot.gs`를 고치고 `node harness2.js` 통과 → 그 폴더의 `Code.js`로 복사 → `npx @google/clasp push -f` → `npx @google/clasp deploy -i <웹앱 배포 ID> -d "설명"`.
- **반드시 `-i`로 기존 웹앱 배포를 갱신**한다(새 배포를 만들면 주소가 바뀌어 중계기 `APPS_SCRIPT_URL`이 끊긴다). 웹앱 배포 ID는 .env `SCHOOL_TODO_KAKAO__CHATBOT_WEBAPP_URL`의 `/s/…/exec` 사이 값. `@HEAD` 배포는 쓰지 않는다.
- 배포 뒤 시험: 중계기 주소로 UTF-8 본문 파일을 보내 확인(윈도우 `curl.exe -d`에 한글을 직접 넣으면 깨진다).
- 중계기 주소·키(`KAKAO_KEY`)는 Cloudflare Secret에 있다. 주소는 `school-relay` 워커.

## 12-2. 친구에게 보내기 받는 사람 등록 (가족·친한 동료, 2026-11-20)
- 공식 제한(developers.kakao.com 메시지 정책, 확인일 2026-11-20): 심사 전 친구 발송은 앱 전체 하루 30건, 한 번에 5명, 받는 사람은 앱 멤버여야 함. 그래서 가족·친한 동료 몇 명용이다. 동료 전체는 이메일 방식(5-D)으로.
- 흐름: 선생님이 카카오 디벨로퍼스 [앱] > [멤버]에 그 사람 카카오계정 이메일을 추가 → 그 사람이 초대 메일 수락 → 등록 링크(웹앱 `…/exec?join=weekly` 또는 `?join=daily`)를 눌러 카카오 동의 → 챗봇이 토큰을 받아 앱 연결만 끝내고(토큰은 버림) `받는사람` 탭에 카카오ID·받기를 적음 → 다음 아침 실행이 선생님 친구 목록에서 카카오ID로 찾아 이름·uuid를 채우고 발송.
- `받는사람` 탭: `이름 | 받기 | 카카오ID | uuid | 등록시각`. 받기 `매일`=아침 일정, `주간출장`=주 1회 출장, 비우면 중지. 기존 Secrets `KAKAO_FRIEND_UUIDS`·`WEEKLY_FRIEND_UUIDS`도 함께 쓴다(합침).
- 챗봇의 카카오 설정값(`KAKAO_REST_API_KEY`, `KAKAO_CLIENT_SECRET`, `KAKAO_REDIRECT_URI`)은 Apps Script 속성에 있다. 바꿀 때는 시트에 `비밀설정` 탭(A=이름, B=값)을 만들면 다음 GET 때 속성으로 옮기고 탭을 지운다.
- 카카오 앱 설정: 리다이렉트 URI에 웹앱 `…/exec` 주소 등록, 동의항목 `카카오 서비스 내 친구목록` 사용. Apps Script는 외부 호출 권한이 필요해 편집기에서 `권한승인` 함수를 한 번 실행해 허용해야 한다.
- 친구에게는 사람당 하루 한 통: 개인 할 일(구분 `개인`)을 뺀 메시지를 `one_message`로 190자 안에 담고, 버튼 `자세히 보기`는 읽기 전용 페이지(웹앱 `?view=VIEW_TOKEN&k=daily|weekly`)를 연다. 페이지 본문은 아침 실행이 `공유링크` 탭(`WEBAPP_URL`, `VIEW_TOKEN`, `DAILY_TEXT`, `WEEKLY_TEXT`, `UPDATED`)에 써 둔 글. `WEBAPP_URL`이 없으면 예전처럼 시트 링크. 카카오 앱 [플랫폼] > [Web]에 `https://script.google.com` 도메인 등록이 필요하다(메시지 링크는 등록 도메인만 열림). 주소 유출 시 `VIEW_TOKEN` 칸을 지우면 다음 실행 때 새로 만든다.
- 알려진 한계(2026-11-20 검토): ① `VIEW_TOKEN`은 하나이고 기한이 없다(메시지가 전달되면 그 주소로 계속 열림 → 칸을 지워 교체). ② `비밀설정` 탭은 지워도 시트 버전 기록에 남는다(시트 편집자는 선생님·서비스 계정뿐이라 감수. 시트를 남과 공유하게 되면 client secret 재발급). ③ 친구용 문구는 `개인` 구분만 뺀다 → **학생 이름을 일정 내용에 쓰지 않는다**(가족 카톡과 공유 페이지로 나감).
- 친구 발송이 실패해도 내 메시지는 계속 보낸다(실패는 로그에 ⚠). `python -m schooltodo friends`는 친구 이름만 출력하고 받는사람 탭을 채운다(uuid는 출력하지 않음).

## 13. 검증 상태 요약
- 확인됨: 아침 카톡 정상 수신, cron-job.org → 깃허브 실행(204), 챗봇 로직 38개와 중계기 10개(가짜 환경), 아침 메시지 규칙(dry-run), 전체 pytest 46개(2026-11-20).
- 미확인: 실제 카카오 ↔ Apps Script/Cloudflare 연결, 사용자별 `user.id` 값, 응답 5초 내 도착, 친구 메시지 실제 발송·`friends` 명령, 구글 메일 한도, 오픈빌더의 정확한 메뉴·항목 이름(기억 기준 부분).

## 14. 노션 (별개)
노션 `2026 업무일지`는 "일에 대한 감상·제안·배운 점"을 쌓는 창고다. 할 일은 노션이 아니라 이 시트에서만 관리한다. 이 프로젝트 코드와는 연결되어 있지 않다.
