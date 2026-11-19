# school-todo-kakao

학교 공용 일정 시트와 내가 직접 적은 할 일을 **내 일정DB 시트 한 곳**에 모으고,
평일 아침마다 그날 일정을 카카오톡 **나에게 보내기**로 알려 주는 작은 파이썬 프로그램입니다.
컴퓨터가 꺼져 있어도 GitHub Actions가 대신 실행합니다.

```
공용 시트(주간·오늘 일정) ─ sync(새 일정만 추가·분류) ─▶ 일정DB(내 구글 시트) ─ morning ─▶ 카톡
                                                         ▲
                                                 내가 직접 적는 할 일
```

- 공용 시트는 **읽기만** 합니다. 고치지 않습니다.
- 일정DB의 `상태`·직접 고친 내용은 sync가 **덮어쓰지 않습니다** (새 키만 추가).
- 로그에는 일정 내용을 남기지 않습니다(공개 저장소에서 실행 로그는 누구나 봅니다).

## 1분 체험 (자격증명 없이)

```bash
pip install -r requirements.txt
python -m schooltodo morning --db-csv tests/fixtures/db.csv --dry-run --today 2026-11-18
python -m schooltodo sync --week-csv tests/fixtures/week.csv --today-csv tests/fixtures/today.csv \
       --db-csv tests/fixtures/db.csv --today 2026-11-18      # 추가될 일정만 미리 보기
python -m pytest -q
```

## 일정DB 시트 만들기

새 구글 시트의 탭 이름을 `일정DB`로 하고 첫 행에 아래 열 이름을 적습니다. 열 순서는 달라도 되고, `대상`은 없어도 동작합니다.

| 키 | 날짜 | 구분 | 내용 | 상태 | 출처 | 대상 |
|---|---|---|---|---|---|---|

- **가족 등에게 주 1회 '출장' 보내기**: 구분이 `출장`인 행만 모아 향후 7일치를 보냅니다(내 대상 행만, ✔ 처리한 행 제외). 깃허브 Secrets `WEEKLY_FRIEND_UUIDS`에 받는 사람 uuid(쉼표, 최대 5명), Variables `WEEKLY_DAY`에 요일(0=월 … 6=일, 기본 월)을 넣으면 매일 아침 실행이 그 요일에만 함께 보냅니다. uuid는 `python -m schooltodo friends`로 조회하고, 시험은 `morning --dry-run --weekly`로 합니다.\n- **구분**: 학교 / 개인 / 출장 / 공지 — **상태**: 끝내면 `✔`. **비어 있는 행만** 메시지에 나갑니다(`검토대기` 같은 값도 제외).
- **출처**: `자동`(sync가 넣음) / 그 외는 내가 적은 것. **지연 알림은 구분이 `개인`인 해야 할 일에만** 뜹니다(기한이 지난 행사 `출장`·`학교`·`공지`는 지연이 아니라 그냥 지나갑니다).
- **구분**: `개인` = 기한이 있는 해야 할 일. 상태 칸에 ✔가 없는 동안 30일 이내 기한이면 `📌 기한 있는 할 일`에 `D-n`과 함께 나옵니다(주 1회 월요일에 전부, 다른 날은 기한 3일 전에 한 번 더. 그 3일 전이 주말이면 금요일에. Variables `TASK_DAY`(0=월 … 6=일, `daily`면 매일)와 `TASK_IMMINENT_DAYS`로 바꿈)(행사는 `학교`·`출장`·`공지`로 적으면 그날과 전 근무일에 나오고, 같은 주 행사는 `🗓 이번 주 남은 일정`에 모아 보여 줍니다. 금요일에는 `🗓 다음 주 일정`).
- **대상**: `전체`·`체육`·`3학년`은 메시지에 나가고 `타학년·유치원`은 DB에만 남습니다. 틀리게 분류됐으면 시트에서 값만 고치면 됩니다.
- 내가 직접 적는 행은 `날짜`(2026-11-18 / 11/18 등)와 `내용`만 있으면 됩니다.

## 설정 (한 번만)

1. **카카오**: 기존에 쓰던 앱·시크릿 이름을 그대로 씁니다(`KAKAO_REST_API_KEY`, `KAKAO_CLIENT_SECRET`, `KAKAO_REFRESH_TOKEN`). 나에게 보내기(`talk_message`) 동의가 된 리프레시 토큰이면 됩니다.
2. **구글 서비스 계정**: Google Cloud에서 프로젝트 → *Google Sheets API* 사용 → 서비스 계정 만들기 → JSON 키 받기 →
   **일정DB 시트를 그 서비스 계정 이메일에 편집자로 공유**합니다.
3. **원본 공용 시트**: '링크가 있는 모든 사용자 보기'로 공유된 시트여야 로그인 없이 읽습니다. 시트 주소의 `/d/<ID>/` 와 `gid=<숫자>`를 적어 둡니다.
4. **GitHub Secrets** (저장소 → Settings → Secrets and variables → Actions):

   | 이름 | 내용 |
   |---|---|
   | `KAKAO_REST_API_KEY` `KAKAO_CLIENT_SECRET` `KAKAO_REFRESH_TOKEN` | 카카오 |
   | `GOOGLE_SERVICE_ACCOUNT_JSON` | 서비스 계정 JSON 파일 내용 전체 |
   | `DB_SHEET_ID` | 일정DB 시트 ID |
   | `SRC_WEEK_SHEET_ID` `SRC_WEEK_GID` | 주간 일정 시트 ID, gid |
   | `SRC_TODAY_SHEET_ID` `SRC_TODAY_GID` | 오늘 일정 시트 ID, gid |
   | `MY_NAME` (선택) | 오늘 일정표 '출장정보'에서 내 출장을 찾을 이름 |
   | `GH_PAT` | 이 저장소의 *Secrets 읽기·쓰기* 권한만 준 fine-grained 토큰. 카카오 리프레시 토큰이 갱신될 때 자동 저장용 |

   시트 ID도 Secrets에 두면 공개 로그에서 `***`로 가려집니다.
5. Actions 탭 → `morning-todo` → **Run workflow**로 한 번 시험합니다. 이후 평일 06:30(한국시간)에 자동 실행됩니다.

로컬에서 돌릴 때는 `.env.example`을 `.env`로 복사해 채웁니다(`GOOGLE_SERVICE_ACCOUNT_FILE`에 키 파일 경로).
`python -m schooltodo morning --dry-run`은 메시지만 출력하고 보내지 않습니다.

## 분류 규칙 바꾸기

`config.example.toml`을 `config.toml`로 복사해 학년과 키워드를 고칩니다. 기본값은 3학년·체육 업무 기준입니다.
체육 키워드가 학년 제외보다 우선합니다(체육 담당은 다른 학년 대회도 챙겨야 하므로).

## 알아둘 점

- **카톡 글자 수**: 나에게 보내기 텍스트는 200자 제한이라, 길면 `(1/2)` 식으로 나눠 보내고 소제목을 이어 붙입니다.
- **카카오 리프레시 토큰**은 2달 유효, 만료 1달 전부터 갱신 응답에 새 토큰이 옵니다. 워크플로가 `GH_PAT`으로 Secrets에 다시 저장하므로 매일 돌면 끊기지 않습니다. `GH_PAT`이 없으면 경고만 남깁니다.
- **공개 저장소는 60일 동안 저장소 활동이 없으면 예약 실행이 자동 중지**됩니다. 멈추면 Actions 탭에서 다시 켜세요.
- **키는 일정 앞 10글자 기준**입니다. 공용 시트의 문구가 바뀌면 같은 일정이 새 행으로 한 번 더 들어올 수 있습니다(DB에서 지우면 됩니다).
- **원본 시트 형식이 바뀌면** `schooltodo/sources.py`의 파서만 고치면 됩니다. 동기화가 실패하면 아침 메시지 끝에 `⚠ 동기화 실패`가 붙습니다.
- 공용 시트가 로그인 없이 읽히지 않으면 `fetch_rows`가 "공용 시트를 읽지 못했습니다"라고 알려 줍니다.

## 올리지 않는 것

`.env`, `config.toml`, 서비스 계정 JSON, `new_refresh_token.txt`, 실제 시트 주소·일정은 저장소에 넣지 않습니다(`.gitignore` 참고).
`tests/fixtures`의 데이터는 모두 가짜입니다.
