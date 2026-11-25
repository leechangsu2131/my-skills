---
name: teacherlesson-assistant
description: "수업 비서. Supabase 진도(lesson_* 표)의 그날 수업을 교시별로 넘겨 보며 왼쪽 창에 수업 흐름·주의점·메모, 오른쪽 창에 출판사 수업 사이트를 띄우고 녹음·메모·알림장 초안·진도 조정을 한 화면에서 한다. '내일 수업 준비해줘', '수업 흐름 만들어줘', '오늘 수업 정리해줘', '출판사 지도서 특징 정리', '수업 비서 켜줘', '지도서 받아줘' 같은 요청에 사용한다."
metadata:
  category: 수업·교사 도구
  status: 개발
  version: v0.1.0
  summary: 진도표·지도서·출판사 사이트·녹음·메모를 묶은 교시별 수업 진행 화면과, 수업 뒤 메모를 정리해 다음 수업에 반영하는 Claude 작업 절차.
---

# 수업 비서 (teacherlesson-assistant)

- **수업 화면** (`assistant_server.py` + `web/index.html`) — Supabase에서 시간표를 읽고 완료·연장·이동을 Supabase에 저장한다. 수업 기록은 로컬 데이터 폴더에 저장한다. Supabase 연결에 중앙 `.env`의 `SUPABASE_URL`(또는 `NEXT_PUBLIC_SUPABASE_URL`)과 `SUPABASE_SERVICE_ROLE_KEY`가 필요하다. 과목별 차시 자료 자동 열기 도우미는 `sites/`(음악 Douclass, 사회 아이스크림·Douclass, Selenium)이며, 미술 아트앤컬쳐 도우미는 아직 구현 전이다(ISSUES ISSUE-006). 실행 방법·화면 기능·저장 위치·지도서 받기는 [README.md](README.md).
- **Claude 작업 절차** (아래) — 화면은 `flows/`·`units/` 를 읽고, 교사가 ✏ 로 고친 흐름은 저장한다(고친 흐름은 자동 준비가 덮어쓰지 않음).

데이터 폴더: `내 문서\my-skills-data\teacherlesson-assistant\` (config, units, flows, sessions, publisher_notes). 학생 이름이 들어간 메모·녹음은 이 폴더에만 두고 기억(memory)·CLAUDE.md·깃·홈페이지에 옮기지 않는다.

## 역할 나눔 (토큰 아끼기)

- **날마다 쓰는 기능은 Claude 토큰 0**: 단원 개관(`build_units.py`), 진도 조정, AI 준비 자료 모으기는 규칙·스크립트로 돈다.
- **수업 상담·많이 읽기는 웹 AI**(Claude·Gemini·ChatGPT·NotebookLM): 화면의 **🤖 AI와 수업 준비** 단추가 지도서 PDF를 모으고 질문을 복사해 AI 사이트를 연다. 학생 메모·녹음은 넣지 않는다.
- **Claude Code(이 스킬)**: 자동화·연결·검토 — 지도서 받기·나누기, 진도표 연결, 화면 기능 고치기, 수업 정리.

## Claude 작업 절차

### A. 수업 흐름 — 자동 준비가 기본 (Claude 토큰 0)

"내일 수업 준비해줘" → `python prepare_lessons.py --date tomorrow` (화면의 **🌙 수업 준비** 단추·아침 bat 와 같은 일). 흐름 없는 차시마다 NotebookLM 소스 md 의 그 차시 구간(없으면 Supabase 차시의 PDF 경로에서 발췌한 쪽)을 Gemini(util-notebooklm, 무료 flash, 붐비면 다른 모델)에 넘겨 `flows/<record_key>.json` 을 만든다. 결과 줄(성공·실패·이유)만 보고한다. 사람이 고친 흐름은 덮어쓰지 않는다(`--redo` 는 자동 흐름만).

아래 손 절차는 교사가 **그 차시를 콕 집어** Claude 에게 직접 만들어 달라고 할 때만 한다.

1. `GET http://127.0.0.1:5180/api/state?date=YYYY-MM-DD`로 Supabase 진도표의 수업을 찾는다.
2. `http://127.0.0.1:5180/api/pdf/<record_key>`(그 차시 쪽만 잘린 PDF)에서 텍스트를 뽑는다. 지도서 전체를 통째로 읽지 않는다.
3. `flows/<record_key>.json`을 쓴다. 지도서 문장은 수업 중 한눈에 보이게 줄인다.

```json
{
  "record_key": "...", "subject": "수학", "title": "분수의 덧셈(2)", "publisher": "아이스크림",
  "source": "지도서 p.120-123", "goal": "학습 목표 한 줄", "materials": ["분수 막대"],
  "steps": [{"name": "도입", "minutes": 5, "do": "할 활동", "say": "핵심 발문", "tip": "주의·보충할 점", "flag": "keep 또는 cut(선택)"}],
  "homework": ""
}
```

4. `tip`에는 그 수업의 `cautions`(출판사 주의점)와 `recent_memos`(같은 과목 지난 고칠점)를 실제로 적용한다.
5. 지도서에서 확인이 안 된 부분(쪽 누락, 스캔 PDF 등)을 보고한다.

### A-2. 단원 개관 — 자동 (Claude 판단 없음)

`py -3.13 build_units.py` (bat 가 12시간마다 실행). 단원 흐름은 진도표 행을 그대로 묶고, 단원 개관 PDF는 1차시 지도서에서 첫 차시 앞쪽을 규칙(`LESSON_START`)으로 자른다. 수학처럼 분할 결과에 plan 묶음이 있으면 그것을 쓴다. `summary`·`goals`·`cautions`·`assessment` 칸은 있으면 보여 주고 지우지 않지만, Claude가 새로 쓰지 않는다.

### A-3. NotebookLM 소스 — "NotebookLM 소스 만들어줘" (학기 초·새 지도서 받은 뒤)

`py -3.13 notebook_sources.py [과목…] [--all]` 를 돌리고 출력 줄(구간 수·단어 수·PDF 없음·⚠ 한도)을 그대로 보고한다. 소스 내용을 Claude가 읽거나 요약하지 않는다. "구간 1개"인 단원은 차시 표시를 못 찾은 것이므로 그 PDF의 차시 머리 모양을 확인해 `KOREAN_LESSON`/`STAGE` 규칙을 고친다. 업로드·노트북 주소 등록은 교사가 한다(README).

차시 번호가 비어 있다고 해당 행을 버리거나 지도서 전체를 Gemini에 넘기지 않는다. `build_units.infer_lesson_numbers()`는 앞뒤 번호가 빈 행 수와 정확히 맞을 때만 번호를 추론한다. NotebookLM 소스 생성 뒤 `prepare_lessons.lesson_section()`이 그 차시 번호 범위 또는 번호 없는 단계 제목으로 올바른 구간을 가져오는지 확인한다.

- 번호 없는 단계 제목 단원(국어 3.5 매체 등)의 매핑과 사례는 ISSUES ISSUE-025.

### B-0. 미술 아트앤컬쳐 사이트 — 도우미 구현 대기

경로·진도 불일치·할 일은 ISSUES ISSUE-006. 도우미를 추가할 때 로그인 값은 코드/config 에 넣지 말고 공용 Chrome 프로필 로그인 세션을 먼저 확인한다. 자동으로 진도를 고치지 말고 실제 진도부터 확인한다.

### C. 수업 정리 — "오늘 수업 정리해줘"

1. `sessions/<날짜>/*.json`을 읽고 과목별 잘된 점·고칠 점을 요약한다.
2. 같은 출판사에서 반복되는 특징(예: "아이스크림: 활동은 재밌지만 개념 설명이 단순")은 `publisher_notes.json` 추가 후보로 제시하고, **교사가 동의한 것만** 넣는다.
3. 🙋 학생 발표 메모는 `observations/<학기>.csv`(날짜, 과목, 차시, 학생, 내용)에 모은다. 평가 문구로 자동 변환하지 않는다(`classmanage-student-eval-generator`의 일).
4. 진도가 실제와 어긋났으면 화면의 진도 조정 단추를 안내한다. 시트 변경은 교사 확인 뒤에만.
5. 녹음은 지금은 클로바노트 등으로 받아쓰고, 받아쓴 텍스트가 있으면 함께 분석한다.

### D. 알림장 — "알림장 올려줘"

v0.1은 "복사하고 하이클래스 열기"까지만. 자동 게시는 ISSUES 다음 단계 1번. 게시 전에는 반드시 교사 확인.

### E. 지도서 받기 — "지도서 받아줘"

`teacherlesson-guide` 스킬로 옮겼다: `python ..\teacherlesson-guide\download\guide_download.py <과목…>` (selenium 설치된 Python) → 같은 스킬의 splitter → mapper.

### F. 수업 메모 동기화 — 부품만 있고 아직 연결 전

`memo_sync.py` 가 수업 메모를 Supabase `lesson_memos` 표에 올리고(`push_session`) 다른 PC 의 것을 받아 `sessions/` 파일에 합친다(`pull`). 서버(`assistant_server.py`)·아침 bat 에는 **아직 연결하지 않았다**. 연결 전에 교사 결정이 필요하다(TASKS T49: 📝·🔧·🎤 자유 글 메모에 학생 이름이 있으면 그대로 올라감).

- 명령: `python memo_sync.py pull [--days N | --since YYYY-MM-DD | --all] [--if-older 시간]`, `python memo_sync.py flush`. 주소·키는 중앙 `.env` 에서 읽고 출력하지 않는다.
- 🙋 학생 메모(`student`)는 절대 올리지도 받지도 않는다. 다른 종류를 더 빼려면 `.env` 의 `TEACHERLESSON_ASSISTANT__MEMO_SKIP_KINDS=step,sys,adj`(올리기만 막음).
- 같은 메모는 `memo_key` 로 한 번만 들어간다. 받은 메모에는 서버의 키를 그대로 저장해 둔다. 키를 다시 계산하면 적은 시각(`at`)이 달라 다른 값이 나와 중복이 생기므로, 저장된 키가 있으면 그것을 쓴다.
- 실제 DB 로 올리기·받기는 교사 확인 뒤에만 한다. 시험은 가짜 서버(`tests/test_memo_sync.py`).

## 연결되는 스킬

- `teacherlesson-schedule` — 옛 Google Sheets 진도표·수업배치(진도 원본은 이제 Supabase, `supabase_schedule.py`. config `schedule_backend` 가 `supabase` 가 아닐 때만 옛 진도 서버 사용)
- `teacherlesson-from-neis` — 나이스 주간학습안내(보결·시간표 변경)
- `teacherlesson-guide` — 지도서 받기·분할·진도표 행 생성
- `admin-hitalk-sender` — 하이클래스 자동 전송 참고
- `util-notebooklm` — 긴 지도서에서 찾기(Gemini CLI)·쪽 잘라내기·NotebookLM 소스·노트북 목록. 지도서를 통째로 읽어야 할 것 같으면 먼저 `nlm.py find`
