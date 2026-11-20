# school-todo-kakao — 에이전트 작업 안내

교사 한 명(3학년 담임·체육업무)의 일정·할 일을 구글 시트 `일정DB`에 모으고, 매일 아침 카카오톡으로 알려 주는 프로젝트.
이 문서는 앞선 Claude 대화에서 정한 규칙과 현재 상태를 담았다. 작업 전에 끝까지 읽을 것.

## 지켜야 할 원칙
- **무료로만** 구성한다. 카카오 챗봇 Event API(챗봇이 먼저 보내기)는 건당 과금·월렛·비즈니스 인증이 필요하므로 쓰지 않는다.
- 비밀값(카카오 키·토큰, 서비스 계정 JSON, 시트 ID, 깃허브 토큰, 챗봇 SECRET, 사람들의 챗봇 아이디·uuid·이메일)은 **절대 커밋하지 않는다.** 깃허브 Secrets / Apps Script 속성 / 시트에만 둔다.
- 학생·학부모 개인정보를 일정 내용에 넣지 않는다(카카오 서버·로그를 거친다).
- 파일 줄바꿈은 기존대로 CRLF를 유지한다.
- 말로 한 약속과 코드가 어긋나면 코드 쪽을 고치고 `안내` 탭(시트)에 기록한다.

## 전체 구조
```
공용 학교 시트 ──(sync)──▶ 일정DB(개인 구글 시트) ──(morning)──▶ 카카오톡(나에게/친구에게 보내기)
빠른입력 탭 ─(sync가 정식 행으로)─┘
cron-job.org ─POST─▶ GitHub Actions(morning.yml, workflow_dispatch) ─▶ python -m schooltodo sync / morning
카카오 채널 + 오픈빌더(폴백 스킬) ─▶ Apps Script 웹앱(chatbot/kakao_chatbot.gs) ─▶ 일정DB·구성원·완료기록
```
- 깃허브 `schedule`(cron)은 몇 시간씩 늦거나 누락돼 **제거**했다. 실행 시각은 cron-job.org가 정하며 **매일**(주말 행사 때문) 호출하고 시간대는 Asia/Seoul.
  호출: `POST https://api.github.com/repos/<소유자>/my-skills/actions/workflows/morning.yml/dispatches`, 헤더 `Authorization: Bearer <fine-grained PAT, Actions read/write>`, `Accept: application/vnd.github+json`, 본문 `{"ref":"main"}`.
- 저장소 이름은 `my-skills`, 이 프로젝트는 `skills/school-todo-kakao/` 하위 폴더(워크플로 `working-directory`).
- `morning.yml`의 guard 단계(예약 중복 방지)는 이제 `schedule` 이벤트가 없어 동작하지 않는다(무해). 필요하면 정리해도 된다.

## 코드 (schooltodo/)
| 파일 | 역할 |
|---|---|
| `cli.py` | `sync`, `morning`(`--dry-run`, `--weekly`, `--db-csv`, `--today`), `friends`(카카오 친구 uuid 조회, 로컬에서만) |
| `message.py` | 아침 메시지 조립: `build_message`, `build_weekend_message`, `build_weekly_trips`, `split_message`(카톡 글자 수 제한으로 나눔) |
| `kakao.py` | 토큰 갱신, 나에게/친구에게 보내기, `list_friends` |
| `sync.py`, `inbox.py`, `classify.py`, `db.py`, `dates.py`, `sources.py` | 공용 시트 → 일정DB 동기화, 빠른입력, 분류, 시트/CSV 입출력(열 이름 기반) |

`cli.py`는 `message.py`·`kakao.py`의 새 함수를 불러오므로 **세 파일은 항상 함께 바꾼다.**

## 일정DB 규칙
열: `키 | 날짜 | 구분 | 내용 | 상태 | 출처 | 대상 | 담당` (코드는 열 이름으로 읽으므로 순서는 바뀌어도 되나 이름은 그대로. `담당`은 선택 열)
- `키` = `MMDD-` + 내용 앞 10글자(공백 제거). sync가 이 키로 중복을 막고, 기존 행은 덮어쓰지 않는다. **완료기록이 키로 연결되므로 키를 고치지 않는다.**
- `날짜` = `yyyy-mm-dd` **텍스트**(열 서식이 텍스트. 날짜값과 섞이면 정렬이 어긋난다).
- `구분`: `개인`=기한 있는 해야 할 일 / `출장`·`학교`·`공지`=행사. 빠른입력은 글에 `출장`이 있으면 `출장`, 아니면 `개인`.
- `출처`: `자동`(sync가 공용 시트에서 가져옴) / `수동`(내가 적음). 지연 판단에는 쓰이지 않는다.
- `상태`: `✔`면 완료(아침 메시지에서 제외). 비어 있어야 알린다.
- `대상`: `타학년·유치원`이면 제외. 그 외(`전체`,`3학년` 등)는 포함.
- `담당`: 이름(쉼표로 여러 명)·그룹 이름·`전체`. 비면 공유 일정이거나 교사 본인의 할 일.
- 일정DB를 정렬할 때는 **H열(담당)까지** 범위에 넣는다.
- 알려진 문제: 공용 시트에 개교기념식이 옛 날짜(11/25)로 남아 있으면 sync가 1125 행을 다시 추가한다. 그 행은 상태 `✔`로 막아 두었다(근본 해결은 공용 시트 날짜 수정).

## 아침 메시지 규칙 (평일)
1. `📅 오늘`: 오늘 일정 · 2. `⚠ 지연`: 구분 `개인`이고 기한이 지났고 상태가 빈 행(행사는 지나가면 그냥 사라짐, 최대 5건)
3. `📌 기한 있는 할 일`: 구분 `개인`, 30일 이내, 최대 5건. **월요일(TASK_DAY)에 전부**, 다른 날은 기한 3일 전(TASK_IMMINENT_DAYS)에 한 번만. 그 3일 전이 주말이면 금요일에. 오늘·다음 근무일 항목은 제외(이미 위에 나옴). `TASK_DAY=daily`면 매일.
4. `👉 다음 근무일 미리보기` · 5. `🗓 이번 주 남은 일정`(금요일에는 `🗓 주말·다음 주 일정`), 구분 `개인`이 아닌 행사만, 최대 6건.
- **주말(토·일)**: 평소 메시지는 보내지 않고, 오늘 행사(출장·학교·공지)가 있을 때만 `📅 오늘` 한 통. 없으면 아무것도 안 보냄.
- **주간 출장 메시지**(가족 등): 구분이 `출장`인 내 행의 향후 7일치를 `WEEKLY_DAY`(기본 월요일)에 `WEEKLY_FRIEND_UUIDS`(최대 5명)에게 보낸다. 나에게 보내는 메시지와는 별개.

## 설정값
- Secrets: `KAKAO_REST_API_KEY`, `KAKAO_CLIENT_SECRET`, `KAKAO_REFRESH_TOKEN`, `KAKAO_FRIEND_UUIDS`, `GOOGLE_SERVICE_ACCOUNT_JSON`, `DB_SHEET_ID`, `SRC_WEEK_SHEET_ID`, `SRC_WEEK_GID`, `SRC_TODAY_SHEET_ID`, `SRC_TODAY_GID`, `MY_NAME`, `GH_PAT`(리프레시 토큰 갱신 저장용), `WEEKLY_FRIEND_UUIDS`
- Variables: `KAKAO_SEND_TO_ME`, `WEEKLY_DAY`(0=월…6=일), `TASK_DAY`, `TASK_IMMINENT_DAYS`

## 카카오 챗봇 v2 (chatbot/)
- 시트 탭: `구성원`(이름·그룹·챗봇아이디·역할(관리자/일반)·이메일), `완료기록`(시각·키·이름·내용; 챗봇이 한 줄씩 추가, 없으면 자동 생성).
- 담당자가 챗봇에 `완료 ○○`/`○○ 완료`/`나 완료했어`(남은 일이 하나일 때)/`되돌리기 ○○`/`할일`/`오늘`. 관리자는 `현황 [키워드]`(✔한 사람/⏳안 한 사람), `완료 ○○ 이름`(대신 처리).
- 일반 사용자는 **자기 몫만** 처리. 담당자가 모두 완료하면 일정DB `상태`에 `✔` 자동.
- 인증: 스킬 URL의 `?key=SECRET`(Apps Script 속성) + 구성원 탭의 챗봇아이디(= 스킬 요청의 `userRequest.user.id`, 종류 botUserKey). `ALLOWED_IDS` 속성은 처음 관리자 등록용.
- 챗봇 아이디는 친구 메시지용 uuid와 **다른 값**이다(섞지 말 것).
- 설치 순서는 `chatbot/kakao_chatbot_setup.md`.

## 검증 상태 (중요)
- 파이썬: 2026-11-20 전체 `pytest` 46개 통과(`pip install -r requirements-dev.txt && pytest`).
- 챗봇: 구글 서비스를 흉내 낸 가짜 환경에서 38개 동작 시험(`chatbot/harness2.js`, `node harness2.js`, 같은 폴더에 `kakao_chatbot.gs`). **실제 카카오·Apps Script 연결은 시험하지 못했다.** Apps Script 웹앱이 오픈빌더 스킬 서버로 받아지는지(리다이렉트), 5초 응답 제한 안에 답하는지 확인이 필요하다.
- 카카오 친구 메시지·`friends` 명령은 실제 호출을 해 보지 못했다(받는 사람의 앱 동의·팀원 등록·심사 조건은 카카오 문서 기준으로 확인할 것: developers.kakao.com 메시지 REST API, kakaobusiness.gitbook.io 챗봇 문서).

## 열린 일 (우선순위 순)
1. 챗봇·카카오 실제 연결을 검증하고 문제를 고친다.
2. **안 한 사람에게만 알리는 이메일**(무료): Apps Script `MailApp`으로 구성원 탭의 이메일에 `담당` 중 완료기록에 없는 사람만 보낸다. 메일 끝에 "챗봇에서 `완료 ○○`라고 보내세요" 안내. 일일 발송 한도 확인.
3. 아침 카톡에 선생님용 현황 요약(완료기록을 읽어 `완료 3/5` 등).
4. (선택) 빠른입력 탭에 `완료 ○○` 명령, 사람별로 읽기 전용 권한 같은 세분화.
5. 선생님이 시트로 바로 완료 처리하는 방법도 병행 중이다(상태 칸에 ✔).

## 참고
- 시트에 `안내` 탭이 있어 규칙·이슈 복구 기록을 적어 두었다(코드 규칙을 바꾸면 같이 갱신).
- 노션 `2026 업무일지`는 이 프로젝트와 별개로 "일에 대한 감상·제안·배운 점"을 쌓는 창고다. 할 일은 노션 Todo DB가 아니라 이 시트에서만 관리한다.
