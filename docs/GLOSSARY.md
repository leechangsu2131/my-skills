# 용어 사전 (쉬운 설명 한 줄씩)

> 이 저장소 문서·코드에서 자주 나오는 말입니다. 뜻은 **오른쪽 '근거' 파일에서 확인한 것만** 적었고, 확인하지 못한 것은 `확인 필요`로 표시했습니다.
> 스킬 이름 `teacherlesson-…` 는 줄여서 `…` 로 씁니다. 틀린 설명을 보면 근거 파일을 먼저 보고 고쳐 주세요.

## 1. 수업·진도

| 용어 | 쉬운 설명 | 근거 |
|---|---|---|
| **진도표** | **무엇을** 가르칠지 적은 표. 한 줄이 가르칠 내용 한 덩어리(차시). 지금 원본은 Supabase, 옛 방식은 Google Sheets | schedule `SKILL.md` "현재 아키텍처", assistant `SKILL.md` |
| **수업배치** | **언제·몇 교시에** 가르칠지 적은 표(옛 Google Sheets 시트) | schedule `SKILL.md` |
| **단원 / 대단원** | 여러 차시를 묶은 큰 덩어리. 단원 개관 파일 이름이 `<과목>__<대단원>` 으로 붙음 | assistant `README.md` 저장 위치 |
| **차시** | 한 단원 안의 수업 한 번 분량. 번호(`lesson_number`)와 제목이 있고, 지도서도 차시별로 쪽을 나눔 | `supabase_schedule.py`, guide `SKILL.md` |
| **교시** | 하루 중 수업 시간 순서(1교시, 2교시…). 차시와 다름: 차시는 **가르칠 내용**, 교시는 **시간 칸** | assistant `README.md`(`교시 시각`), `supabase_schedule.py`(`slot_period`) |
| **슬롯** | 날짜+교시 한 칸에 차시를 놓은 자리. Supabase 의 `lesson_slots` 표에 있고 상태(`planned` 예정 / `done` 완료)가 있음 | `supabase_schedule.py` |
| **완료** | 슬롯 상태를 `done` 으로 바꾸는 것. 화면에서 사라지지 않고 '완료됨'으로 남김. 같은 차시가 여러 슬롯에 걸치면 **마지막 예정 슬롯까지** 끝나야 진도표에서 완료 | schedule `SKILL.md` "완료 처리" |
| **한 차시 더 (연장)** | 이 수업이 다음 같은 과목 시간까지 이어지게 한 차시를 더 잡고, 뒤쪽 같은 과목 수업을 한 칸씩 뒤로 밉니다 | schedule `SKILL.md` "빠른 조정" |
| **다음 차시 당겨오기** | 현재 자리에 같은 과목의 다음 수업을 당겨오고, 뒤쪽 수업은 한 칸씩 앞으로 | 같은 곳 |
| **과목 전체 뒤로 밀기** | 어느 날짜 이후의 그 과목 예정 수업을 한꺼번에 미룸 | 같은 곳 |
| **교환** | 필요할 때만 두 슬롯의 날짜·교시를 맞바꿈. 하루 안 교시 순서 바꾸기가 아님 | 같은 곳 |
| **따라잡기 (catch-up)** | 서버에 `/api/catch-up` 가 있고 진도 조정에 쓰임. 화면의 어느 단추(📍 여기부터 다시 잡기?)와 같은지는 **확인 필요** | assistant `README.md`, `docs/TASKS.md` T27 |

## 2. 식별 이름 (헷갈리기 쉬움)

| 용어 | 쉬운 설명 | 근거 |
|---|---|---|
| **`lesson_id`** | 같은 이름이 **자리마다 다른 값**입니다. ① 옛 Google Sheets: 진도표와 수업배치를 잇는 고정 키(`_row` 보다 우선). ② Supabase 슬롯 표: 차시 표(`lesson_lessons`)의 `id` 를 가리킴. ③ 진도표 형태로 돌려주는 응답: `lesson-0075` 같은 `legacy_lesson_id` 값 | schedule `SKILL.md`, `supabase_schedule.py` 23·190~196행 |
| **`legacy_lesson_id`** | Supabase 차시 표의 옛 차시 번호 칸. 예: `lesson-0075` | assistant `README.md`, `supabase_schedule.py` |
| **`record_key`** | 수업 비서가 한 차시를 부르는 이름. Supabase 차시에서는 `legacy_lesson_id` 값과 같음. 흐름 파일 이름(`flows/<record_key>.json`)과 PDF 주소(`/api/pdf/<record_key>`)에 씀 | assistant `README.md` 47행, `supabase_schedule.py` 117행 |
| **`_row`** | 옛 시트의 행 번호. `lesson_id` 가 있으면 그것이 우선 | schedule `SKILL.md` |

## 3. 수업 비서의 파일과 기능

| 용어 | 쉬운 설명 | 근거 |
|---|---|---|
| **수업 비서** | 교시별 수업 진행 화면(서버 `127.0.0.1:5180`). 진도표·지도서·출판사 사이트·메모를 한 화면에 묶음. 실행은 `실행_수업비서.bat` | assistant `README.md`·`SKILL.md` |
| **흐름 (수업 흐름, `flows/`)** | 한 차시를 단계별로 적은 글: 목표·준비물·단계(활동, 💬발문, 💡팁). 사람이 ✏ 로 고친 흐름은 자동 준비가 덮어쓰지 않음 | assistant `README.md` 36행, `SKILL.md` 14행 |
| **🌙 수업 준비 (자동 준비)** | 그날 **흐름이 없는 차시**마다 흐름을 자동으로 만드는 기능. 화면 단추 또는 `prepare_lessons.py --date today\|tomorrow`. `--redo` 는 자동으로 만든 것만 다시 만듦 | assistant `README.md` 13행 |
| **단원 개관 (`units/`)** | 단원의 차시 목록과 개관 PDF. `build_units.py` 가 규칙으로 만듦(Claude 판단 없음). 12시간마다 bat 가 실행 | assistant `SKILL.md` A-2 |
| **지도서** | 출판사가 내는 교사용 책 PDF. 받아서 차시별로 나눈 뒤 진도표 행을 만듦 | guide `SKILL.md` |
| **출판사 주의점 (`publisher_notes.json`)** | `출판사\|과목` 별로 쌓아 둔 짧은 메모. 반복되는 특징은 **교사가 동의한 것만** 넣음 | assistant `README.md` 52행, `SKILL.md` C |
| **세션 (`sessions/`)** | 그 수업 하나의 메모·알림장·시작/마침 시각(`<날짜>/<교시>교시_<과목>.json`)과 녹음 | assistant `README.md` 48~49행 |
| **NotebookLM 소스** | 지도서를 구간으로 나눠 NotebookLM 에 올릴 글(`notebooklm/<과목>/<대단원>.md`). 업로드는 교사가 함 | assistant `README.md`·`SKILL.md` A-3 |
| **알림장** | 내용을 쓰면 클립보드에 복사하고 하이클래스를 엶. 자동 게시는 아직 없음 | assistant `README.md` 38행 |
| **학생 발표 메모 (`observations/`)** | 수업 중 발표한 학생 메모를 `observations/<학기>.csv` 에 모은 것. 평가 문구로 자동 변환하지 않음 | assistant `SKILL.md` C |

## 4. 학교 업무

| 용어 | 쉬운 설명 | 근거 |
|---|---|---|
| **NEIS (나이스)** | 학생 기록을 입력하는 교육행정 시스템. 제출·입력 같은 실제 실행은 교사 확인 뒤에만 | `admin-neis-bot`, `classmanage-evaluate-to-neis` `SKILL.md` |
| **누가기록** | 관찰일자와 행동특성 내용을 날짜별로 쌓아 둔 기록. 파일로 정리해 NEIS 행동특성 누가기록 화면에 입력 | `classmanage-evaluate-to-neis` `SKILL.md` 169~176행 |
| **에듀파인** | 공문을 받고 처리하는 시스템(K-에듀파인 문서등록대장 등) | 루트 `README.md` "업무 처리 흐름" |

## 5. 저장소·작업 규칙

| 용어 | 쉬운 설명 | 근거 |
|---|---|---|
| **스킬** | `skills/` 아래 독립 폴더 하나. `SKILL.md`(무엇을·언제·어떻게)와 `ISSUES.md`(문제·할 일)가 필수 | 루트 `README.md` |
| **`ISSUES.md`** | 스킬별 문제·해결 기록. 🔵 진행 중 / 📌 백로그 / 🟢 해결됨 세 절 | 루트 `README.md` |
| **`CATALOG.md`** | 스킬 목록. `tools/build_catalog.py` 가 만들므로 **직접 고치지 않음** | `CLAUDE.md` |
| **중앙 `.env`** | 비밀값(키·비밀번호)을 모아 두는 파일 한 곳(교사 PC 의 `OneDrive\96. 인증\.env`). 코드는 `skill_env.py` 로 읽음 | 루트 `README.md` |
| **`data_dir()`** | 학생 정보·결과물·로그인 세션을 두는 폴더(`내 문서\my-skills-data\<스킬>\`). 깃에 올리지 않음 | 루트 `README.md` |
| **작업자** | 이 저장소를 돕는 AI·사람. 등급 **R**(브랜치·PR 가능) · **P**(교사 PC 에서만) · **T**(글만) | `docs/WORKER_GUIDE.md` §2 |
| **일지 (`docs/worklog/`)** | 작업자가 `시작`·`PR 올림`·`막힘`·`그만둠` 을 한 줄씩 적는 곳. 남의 일지는 고치지 않음 | `docs/WORKER_GUIDE.md` §2-1 |
| **가짜 (mock)** | 시험에서 실제 서버·사이트·비밀값 대신 쓰는 흉내 | `docs/WORKER_GUIDE.md` §3 |
| **`DRY_RUN`** | 실제로 보내거나 바꾸지 않고 연습만 하는 설정 이름의 한 종류. 스킬마다 있는지 다름 — 확인된 곳: `util-school-print`(`UTIL_SCHOOL_PRINT__DRY_RUN`). 다른 스킬은 해당 `SKILL.md` 에서 **확인 필요** | `CLAUDE.md`, `util-school-print` `SKILL.md` |
