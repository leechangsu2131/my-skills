# 수업 비서 — 사람용 안내

Claude 작업 절차는 [SKILL.md](SKILL.md), 문제·할 일은 [ISSUES.md](ISSUES.md), 해결 과정과 운영 정보는 [WORKLOG.md](WORKLOG.md).

## 실행

- `실행_수업비서.bat` → 서버(127.0.0.1:5180)가 켜지고 화면 왼쪽 1/3에 수업 비서 창이 열린다. 12시간에 한 번 `build_units.py`(단원 개관)도 돌린다.
- 시간표·완료·연장·미루기·따라잡기는 Supabase를 읽고 쓴다. 중앙 `.env`에 `SUPABASE_URL`(또는 `NEXT_PUBLIC_SUPABASE_URL`)과 `SUPABASE_SERVICE_ROLE_KEY`가 있어야 한다. 진도 서버(5000번)는 이전 Google Sheets 기능을 사용할 때만 필요하다.
- "수업 사이트 열기"는 수업 도우미 공용 Chrome 프로필(config `chrome_profile`, 기본 `%LOCALAPPDATA%\MusicClassHelper\chrome_profile`, 원격 디버깅 포트 `debug_port` 9233)로 화면 오른쪽 2/3에 창을 연다. 열 수 있는 주소는 config 의 과목 사이트·바로가기·하이클래스·AI 사이트 주소뿐이다. 한 번 로그인하면 그 프로필에 로그인이 유지된다.
- 9222 포트는 다른 자동화(에듀파인)가 쓰고 있을 수 있어 9233을 쓴다.
- 서버는 Host 가 127.0.0.1/localhost 인 요청만 받는다(다른 사이트·DNS 리바인딩 차단). 클립보드로 복사한 비밀번호는 30초 뒤 지운다.
- 최초 설정은 `python -m pip install -r requirements.txt`. 서비스 키는 로컬 Python 서버에서만 읽고 브라우저로 보내지 않는다.
- 수업 흐름 자동 준비: 화면의 🌙 단추, 아침 bat 이 오늘 것을 자동으로 돌린다. 손으로는 `python prepare_lessons.py --date today|tomorrow [--redo]`(`--redo` 는 자동으로 만든 흐름만 다시 만들고 사람이 고친 것은 그대로).

## 화면 기능 (v0.1)

| 영역 | 내용 |
|---|---|
| 위쪽 | 날짜 이동(달력·요일·'오늘'), 🌙 수업 준비(그날 흐름 없는 차시를 Gemini 로 자동 준비, `prepare_lessons.py`, 아침 bat 에서도 오늘 것 자동), 시계, 교시 탭(지금 교시 노란 테두리, 📋 흐름 준비됨, ✓ 기록 저장됨), 📞 내선번호 |
| 수업 제목 | 과목·출판사·단원·차시, 수업 사이트 열기, 📂 차시 자료 바로 열기(`sites/` 도우미, config `subjects.<과목>.helper`), 아이디/비번 복사, 지도서 PDF(Supabase 차시 경로) |
| **지금 할 일** | 수업 중 맨 위 큰 카드: 현재 단계·💬 핵심 발문·활동·💡 팁, 단계 남은 시간(1분 이하 주황 / 초과 빨강 `+mm:ss`), 교시 종료까지 남은 분, 다음 단계 미리보기. `다음 단계 ▶` 단추·← → 키·발표 리모컨(PageUp/PageDown)으로 넘김. `−1분`/`+1분` 단추·`+` `−` 키로 이 단계 시간만 이번 수업에서 조정(흐름 파일은 그대로). 시간표 대비 `계획보다 N분 늦음 · 교시 끝까지 N분 모자라요` 안내. 시작 전에는 시간표 시각으로 "지금쯤 어느 단계" 추천. 새로고침해도 단계·시간 유지. 큰 숫자 옆 `−1분`/`+1분`(또는 `+` `−` 키)으로 그 단계 시간을 이번 수업에만 조정하고, `⏱ 계획보다 N분 늦음 · 교시 끝까지 N분 모자라요` 안내와 함께 시간이 모자라면 `✂ 줄여도 되는 단계`(단계 `flag: cut`)를 알려 준다. 흐름(`flows/*.json`)이 없으면 🌙 준비 안내 |
| 🤖 AI와 수업 준비 | 단원 개관·차시 지도서 PDF(+NotebookLM 차시 노트)를 `ask/<날짜>/<교시>_<과목>/`에 모아 폴더 열기 + 질문 복사 + 고른 AI 사이트 열기. NotebookLM 은 과목 노트북을 열고 질문만 복사 |
| 주의할 점 | 출판사별 주의점(`publisher_notes.json`) + 같은 과목 지난 수업 메모·고칠점 |
| 📗 단원 개관 | `units/*.json`의 단원 흐름(지금 차시 ◀)·목표·유의점·평가, 단원 개관 PDF (접기/펴기) |
| 수업 흐름 전체 (접이식) | `flows/*.json`의 목표·준비물·전체 단계(활동, 💬발문, 💡팁). 단계를 눌러 바로 이동 가능. 단계 이동 시 시각 기록(`sessions` 메모의 `step`, `idx` 포함). **✏ 흐름 고치기/직접 만들기**로 화면에서 편집(목표·준비물·단계 이름·분·활동·발문·팁·중요도 ⭐꼭 해야 함/✂ 줄여도 됨)·저장(`POST /api/flow`, 고친 흐름은 자동 준비가 덮어쓰지 않음) |
| 수업 기록 | 녹음(10초마다 서버에 이어 저장), 👍좋았음 🔧고칠점 🙋학생 발표 ★표시 🎤음성 메모, 직접 입력 메모. 모두 녹음 기준 [mm:ss] |
| 알림장 | 내용 작성 → 클립보드 복사 + 하이클래스 열기 (자동 게시는 아직 없음) |
| 진도 조정 | ✅ 완료 / 📍 여기부터 다시 잡기 / 한 차시 더 / 며칠 미루기 → Supabase 수업 슬롯에 바로 반영. 단원·차시·제목 검색으로 진도를 찾는다. 실행 전 확인 창 |

## 저장 위치 (깃에 올리지 않음)

`내 문서\my-skills-data\teacherlesson-assistant\`

- `config.json` — 교시 시각, 내선번호, 바로가기, 과목별 출판사·사이트·`secret_prefix`, `schedule_backend`, `ai_sites`. 처음 실행 때 `config.example.json`을 복사해 만든다.
- `units/<과목>__<대단원>.json`·`.pdf` — 단원 개관 (`build_units.py`가 만든다)
- `flows/<record_key>.json` 또는 `flows/<과목>__<차시제목>.json` — 수업 흐름 (선택). Supabase 차시의 record_key 는 `lesson-0075` 같은 차시 번호(`lesson_lessons.legacy_lesson_id`)
- `sessions/<날짜>/<교시>교시_<과목>.json` — 그 수업의 메모·알림장·시작/마침 시각
- `sessions/<날짜>/<교시>교시_<과목>_<시각>.webm` — 녹음
- `ask/<날짜>/<교시>_<과목>/` — 웹 AI에 끌어다 놓을 PDF와 질문.txt
- `notebooklm/<과목>/` — NotebookLM 소스(`<대단원>.md`, `_그림.pdf`), `notes/` 차시별 노트, `목록.txt`
- `publisher_notes.json` — `{"출판사|과목": [{"text","date"}], "출판사|*": [...]}`

아이디·비밀번호는 중앙 .env(`OneDrive\96. 인증\.env`)에 `<secret_prefix>_ID`, `<secret_prefix>_PW`로 적는다(예: `ISCREAM_ID`). 서버는 값을 화면에 보내지 않고 클립보드로만 넘긴다.

## NotebookLM 소스 (학기에 한 번)

공용 도구는 [`util-notebooklm`](../util-notebooklm/SKILL.md)(글자 뽑기·그림 PDF·md 자르기·노트북 목록·Gemini 찾기). 여기 있는 것은 진도표 차시에 맞추는 수업용 부분이다.

1. `py -3.13 notebook_sources.py [과목…] [--all] [--open]` — 진도표의 단원마다 `notebooklm/<과목>/<대단원>.md` 를 만든다(LLM 없음, 전 과목 30초 안팎).
   - 지도서 글자만 뽑고 차시마다 `## [수학 6단원] 4차시 제목 (지도서 p.25~28)` 표시를 심는다. 쪽마다 `〔p.N〕`.
   - 국어 단원 한 권은 쪽 머리의 `3~4차시 / 14차시`, 매체 단원은 `이 차시는 '다가가기' 학습` 표시로 차시를 나눈다.
   - 글자가 거의 없는 쪽과 음악·미술(`notebooklm_image_subjects`) 단원 전체는 `<대단원>_그림.pdf`(흑백, 쪽마다 차시 표시)로 따로 만든다.
   - 지도서 PDF가 이 PC에 없는 차시는 제목만 넣고 "PDF 없음"으로 알려 준다(지금 음악).
2. 과목마다 노트북을 하나 만들고 그 과목 폴더의 `.md`·`_그림.pdf` 를 소스로 올린다(공개 API가 없어 직접). 한도: 소스당 50만 단어/200MB.
3. 노트북 주소를 `C:\Python313\python.exe ..\util-notebooklm\nlm.py nb add 수업-수학 <주소>` 로 등록한다(또는 `config.json` 의 `subjects.<과목>.notebooklm`) → 🤖 줄의 **NotebookLM** 단추가 그 노트북을 열고 `[과목 N단원] N차시` 를 짚는 질문을 복사한다(파일은 모으지 않음).
4. 답을 오빠두엑셀 북마클릿 등으로 md 로 받았다면 `python split_notes.py 받은.md` → `notebooklm/<과목>/notes/<N단원>_<N>차시.md` 로 잘린다. 그 차시에 다른 AI 단추를 누르면 이 노트도 `ask/` 폴더에 함께 들어간다.

## 지도서 받기

[`teacherlesson-guide/download`](../teacherlesson-guide/download/README.md) 로 옮겼다(2026-11-22). 크롬 프로필·포트 설정은 여기 config 를 같이 쓴다.

## 고칠 때 볼 곳

- 화면: `web/index.html` (한 파일)
- 서버·저장 형식: `assistant_server.py`
- 시간표 조회·진도 변경(Supabase): `supabase_schedule.py`. 수업 흐름 자동 준비: `prepare_lessons.py`
- 자동 시험(표준 라이브러리만, 임시 폴더·가짜 서버라 실제 데이터·DB 를 안 건드림): 이 폴더에서 `python -m unittest test_assistant_server test_supabase_schedule`
- 단원 개관 규칙: `build_units.py` (`LESSON_START`)
- 과목별 차시 자료 도우미: `sites/music_douclass/`, `sites/social_class/` (각 README). 서버의 `SITE_HELPERS` 에 등록
- NotebookLM 소스·노트: `notebook_sources.py`, `split_notes.py` (차시 표시 규칙 `lesson_tag` 은 `assistant_server.py`)
- 설정 항목: `config.example.json` (실사용 설정은 데이터 폴더의 `config.json`)
