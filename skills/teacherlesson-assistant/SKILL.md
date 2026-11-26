---
name: teacherlesson-assistant
description: "수업 비서. Supabase 진도(lesson_* 표)의 그날 수업을 교시별로 넘겨 보며 화면 왼쪽에 수업 흐름·주의점·메모를 띄우고 오른쪽에는 출판사 수업 사이트를 배치한다. 녹음·메모·알림장 초안·진도 조정을 한 화면에서 한다. '내일 수업 준비해줘', '수업 흐름 만들어줘', '오늘 수업 정리해줘', '출판사 지도서 특징 정리', '수업 비서 켜줘', '지도서 받아줘' 같은 요청에 사용한다."
metadata:
  category: 수업·교사 도구
  status: 개발
  version: v0.1.0
  summary: 진도표·지도서·출판사 사이트·녹음·메모를 묶은 교시별 수업 진행 화면과, 수업 뒤 메모를 정리해 다음 수업에 반영하는 Claude 작업 절차.
---

# 수업 비서 (teacherlesson-assistant)

- **수업 화면** (`assistant_server.py` + `web/index.html`) — Supabase에서 시간표를 읽고 완료·연장·이동·오늘 교시의 과목 변경을 Supabase에 저장한다. 수업 비서는 왼쪽 모니터 약 1/3, 수업 사이트는 오른쪽 모니터 전체를 쓴다(오른쪽 화면이 없으면 왼쪽 화면의 나머지 영역). `🎯 수업 진행`은 수업 단계·발문·활동·남은 시간에 집중하는 모드이고, 오늘 저장된 녹음은 화면에서 찾아 재생·저장할 수 있다. 수업 기록은 차시 ID별로 로컬 데이터 폴더에 저장한다. Supabase 연결에 중앙 `.env`의 `SUPABASE_URL`(또는 `NEXT_PUBLIC_SUPABASE_URL`)과 `SUPABASE_SERVICE_ROLE_KEY`가 필요하다. 과목별 차시 자료 자동 열기 도우미는 `sites/`(음악 Douclass, 사회 아이스크림·Douclass, Selenium)이며, 미술 아트앤컬쳐 도우미는 아직 구현 전이다(ISSUES ISSUE-006). 실행 방법·화면 기능·저장 위치·지도서 받기는 [README.md](README.md).
- **Claude 작업 절차** (아래) — 화면은 `flows/`·`units/` 를 읽고, 교사가 ✏ 로 고친 흐름은 저장한다(고친 흐름은 자동 준비가 덮어쓰지 않음).

교사가 화면 쓰는 법을 물으면 [README.md](README.md)의 "교사용 사용 설명서 (한 장)"를 쉬운 말로 안내한다(순서: 날짜·교시 → ☀ 오늘 준비 또는 🌙 내일 준비 → 지금 할 일 → 메모 → 진도 조정). 연락처 안내는 로컬 `config.json`의 `phones`에 있는 내선만 보여 주며, 외부 번호나 개인 휴대전화는 코드·문서·저장소에 옮기지 않는다.

데이터 폴더: `내 문서\my-skills-data\teacherlesson-assistant\` (config, units, flows, sessions, publisher_notes). 학생 이름이 들어간 메모·녹음은 이 폴더에만 두고 기억(memory)·CLAUDE.md·깃·홈페이지에 옮기지 않는다.

## 역할 나눔 (토큰 아끼기)

- **날마다 쓰는 기능은 Claude 토큰 0**: 단원 개관(`build_units.py`), 진도 조정, AI 준비 자료 모으기는 규칙·스크립트로 돈다.
- **수업 상담·많이 읽기는 웹 AI**(Claude·Gemini·ChatGPT·NotebookLM): 화면의 **🤖 AI와 수업 준비** 단추가 지도서 PDF를 모으고 질문을 복사해 AI 사이트를 연다. 학생 메모·녹음은 넣지 않는다.
- **Claude Code(이 스킬)**: 자동화·연결·검토 — 지도서 받기·나누기, 진도표 연결, 화면 기능 고치기, 수업 정리.

## Claude 작업 절차

### A. 수업 흐름 — 자동 준비가 기본 (Claude 토큰 0)

"내일 수업 준비해줘" → `python prepare_lessons.py --date tomorrow` (화면의 **🌙 수업 준비** 단추·아침 bat 와 같은 일). 흐름 없는 차시마다 지도서에서 그 차시 구간을 가져와 Gemini가 먼저 수업 형태·단계·시간을 정하고, 두 번째 요청에서 각 단계를 교사 행동·발문·학생 활동·예상 반응·지원·확인점으로 채운다. 수업 활동에 맞게 4~8개 단계로 구성하고 합계는 40분으로 잡는다. 지도서에 없는 내용은 "운영 제안"으로 구분하며 학생의 구체적인 개인 경험을 지어내지 않는다. 결과 줄(성공·실패·이유)만 보고한다. 사람이 고친 흐름은 덮어쓰지 않는다(`--redo` 는 자동 흐름만).

아래 손 절차는 교사가 **그 차시를 콕 집어** Claude 에게 직접 만들어 달라고 할 때만 한다.

1. `GET http://127.0.0.1:5180/api/state?date=YYYY-MM-DD`로 Supabase 진도표의 수업을 찾는다.
2. `http://127.0.0.1:5180/api/pdf/<record_key>`(그 차시 쪽만 잘린 PDF)에서 텍스트를 뽑는다. Supabase 경로가 다른 PC의 `pdf_splits`를 가리키면 `teacherlesson-schedule.schedule.resolve_pdf_path()`가 경로의 `N단원`을 이용해 같은 단원 폴더 또는 한 단계 위 학년 폴더의 원본 지도서를 찾는다. 지도서 전체를 통째로 읽지 않는다.
3. `flows/<record_key>.json`을 쓴다. 지도서 문장은 수업 중 한눈에 보이게 줄인다.

```json
{
  "record_key": "...", "subject": "수학", "title": "분수의 덧셈(2)", "publisher": "아이스크림",
  "source": "지도서 p.120-123", "lesson_type": "모둠 탐구", "goal": "학습 목표 한 줄", "materials": ["분수 막대"],
  "steps": [{"name": "관찰하기", "minutes": 5, "teacher_actions": ["자료를 나눠 준다"], "teacher_prompts": ["무엇이 보이나요?"], "student_actions": ["자료를 살펴보고 말한다"], "expected_responses": ["학생마다 다른 관찰 내용을 말할 수 있어요"], "teacher_support": "잘 보이지 않으면 일부를 가려 비교하게 한다", "check": "근거를 들어 말하는지", "tip": "주의점", "flag": "keep 또는 cut(선택)"}],
  "homework": ""
}
```

4. `tip`에는 그 수업의 `cautions`(출판사 주의점)와 `recent_memos`(같은 과목 지난 고칠점)를 실제로 적용한다.
5. 지도서에서 확인이 안 된 부분(쪽 누락, 스캔 PDF 등)을 보고한다.

### A-1. 오늘 교시 과목 바꾸기

실제로 수업하지 않는 과목이 오늘 예정 슬롯에 있으면 **진도 조정 → 과목·차시 바꾸기**에서 다른 과목의 미완료 차시를 고른다. Supabase 예정 슬롯에서만 동작한다. 확인 뒤 선택한 차시를 오늘 슬롯으로 옮기며, 기존 과목 차시는 완료 처리하지 않고 다음 같은 과목 시간으로 넘긴다. 기존 과목의 뒤 차시도 각 다음 같은 과목 슬롯으로 이동하고, 현재 계획 끝을 넘는 마지막 차시는 날짜 없는 `planned` 슬롯으로 남긴다. 선택 과목에서 선택한 차시보다 앞선 미완료 차시는 완료 처리하고, 선택 뒤 차시는 그 과목의 기존 예정 슬롯에 순서대로 배치한다. 날짜 지난 슬롯이나 실제 수업 여부가 불확실할 때는 자동으로 바꾸지 말고 교사가 차시를 확인하게 한다. 구현 기록은 ISSUES ISSUE-032.

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

## 연결되는 스킬

- `teacherlesson-schedule` — 옛 Google Sheets 진도표·수업배치(진도 원본은 이제 Supabase, `supabase_schedule.py`. config `schedule_backend` 가 `supabase` 가 아닐 때만 옛 진도 서버 사용)
- `teacherlesson-from-neis` — 나이스 주간학습안내(보결·시간표 변경)
- `teacherlesson-guide` — 지도서 받기·분할·진도표 행 생성
- `admin-hitalk-sender` — 하이클래스 자동 전송 참고
- `util-notebooklm` — 긴 지도서에서 찾기(Gemini CLI)·쪽 잘라내기·NotebookLM 소스·노트북 목록. 지도서를 통째로 읽어야 할 것 같으면 먼저 `nlm.py find`
