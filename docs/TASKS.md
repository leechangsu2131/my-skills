# 할 일 목록 (작업자 공용)

> 규칙은 [WORKER_GUIDE.md](WORKER_GUIDE.md). 등급: **R** 저장소 브랜치·PR 가능(Codex·Claude 웹·Antigravity 등) / **P** 교사 PC 에서만(Antigravity·bizcoder·로컬 Claude Code — 지도서·Supabase·크롬 로그인을 씀). 글만 쓰는 T 등급(ChatGPT 웹)은 2026-11-26 부터 맡기지 않는다(저장소를 못 바꿔 교사 손이 더 듦).
> 상태: `열림` · `진행 중(브랜치)` · `검토 대기` · `완료`. 상태는 교사 PC 에서 합칠 때 고칩니다(작업자는 이 파일을 고치지 않음).
> 브랜치 이름: `task/<번호>-<짧은-설명>`. 같은 번호의 원격 브랜치가 있으면 이미 누가 하는 중입니다.
> **맡기는 기준(2026-11-26)**: 양이 많고 시험으로 확인되는 일(시험·문서·번역·버그 하나 고치기)은 작업자에게. 핵심 파일을 조금 고치는 일(진도 계산·잠금·서버 경로)과 교사 판단이 필요한 일은 **P(교사 PC 의 Claude Code)** — 검토 비용이 직접 하는 비용보다 커서.
> **공용 파일 주인**: `.github/workflows/check.yml` 은 한 번에 한 작업자만(브랜치 이름에 `ci`). 다른 작업자는 고칠 내용을 자기 PR 설명에 적는다.
> **일 받기(2026-11-27)**: 작업자는 번호를 고르지 않고 `python tools/claim_task.py --next --name <이름>` — 하던 일 → 멈춘 일 이어받기(2시간·`그만둠`) → 아래 순서의 '열림' 일. [WORKER_GUIDE 2-1](WORKER_GUIDE.md).
> 고르는 순서(claim_task.py --next): K I G H J E
> 마지막 정리: 2026-11-27

## ★ 지금 집중: 수업 비서 (교사 결정 2026-11-26)

교사가 매일 쓰는 것은 **수업 비서**다. 당분간 작업자는 아래 묶음만 고친다(다른 스킬은 잘 안 써서 고쳐도 도움이 안 됨).

| 묶음 스킬 | 왜 |
|---|---|
| `teacherlesson-assistant` (수업 비서 본체, `sites/` 차시 자료 도우미 포함) | 매일 씀 |
| `util-notebooklm` | 🌙 수업 준비가 부름(`nlm.py`) |
| `teacherlesson-guide` | 지도서를 차시로 나눔(`auto_split.py`) |
| `teacherlesson-schedule` | 옛 진도 서버 — 수업 비서가 부르는 부분만 |
| `teacherlesson-from-neis` | 시간표 변경을 수업 비서에 보여 줄 때만(T84) |
| 저장소 공용 `tools/`·`docs/` | 작업자 협업 |

- 고르는 순서: **K(수업 비서 큰 일, 체크리스트) → I(수업 비서 다음 일) → G → H → J → E** → 상시 일(S, 묶음 안에서만). `claim_task.py --next` 가 이 순서로 고른다.
- **상시 일(S)은 고를 일이 정말 없을 때만** — 2026-11-27 저녁 S1 시험·S2 검토 브랜치가 20개 넘게 쌓였다. K 일이 있으면 K 가 먼저. D 와 P 등급 일은 교사 PC 작업자(Antigravity 등)만.
- 묶음 밖 스킬에서 문제를 보면 고치지 말고 그 스킬 `ISSUES.md` 에 한 줄만 적는다. 묶음 밖 '열림' 일은 `보류`(교사가 쓴다고 하면 다시 엶).

## ★ 큰 프로젝트 — Codex·Antigravity (교사 결정 2026-11-26)

Codex·Antigravity 는 토큰이 넉넉하고 교사와 길게 이야기하며 일한다 → 작은 T 번호 대신 **큰 개선 프로젝트**를 통째로 맡는다.
작은 T 번호 일은 Claude 웹 작업자 몫. 프로젝트가 흡수한 T 번호는 상태가 `프로젝트 P<n>` 이라 다른 작업자가 잡지 못한다(`claim_task.py` 가 막음).
일하는 법·합치는 법: [WORKER_GUIDE.md 2-2](WORKER_GUIDE.md). 막히면 교사 PC 의 Claude Code 가 돕는다.

| 프로젝트 | 맡은 이 | 목표 | 흡수한 일 | 주로 고치는 파일(이 프로젝트 영역) | 상태 |
|---|---|---|---|---|---|
| P1 | 로컬 IDE — Antigravity (ag-1) | 교실 도구·학생 명단: 타이머·발표자 뽑기·소음 측정, 명단에서 🙋 학생 고르기, 주간 정리 이름 가리기, **학생별 기록 모아보기(🙋 관찰·결석·상담 — 데이터 폴더에만, ISSUE-052 ⑥ 2026-11-28 추가)** | T70, T89 (+ T53 점검표) | 새 `web/tools.js`·`tests/test_tools.js`, 명단 읽기, `weekly_report.py` | 진행 중 — 교실 도구·점검표 합침(2026-11-26), 남은 것: 명단에서 🙋 이름 고르기·주간 정리 이름 가리기 |
| P2 | 로컬 IDE — Codex (교사와 함께) | 휴대폰(전화)에서 쓰는 기능·화면 개선 | — | 화면 배치·스타일(가능하면 새 `web/*.css`·`web/*.js`) | 진행 중 — 1차(휴대폰 화면 `web/mobile.css`) 합침 2026-11-26 |
| P3 | (비어 있음) | 차시 자료 바로 열기 완성: 이름 맞추기, 미술·사회 도우미 | T82, T87, T88 | `sites/` | 열림 |
| P4 | (비어 있음) | 진도 안정화: 따라잡기 뒤 뒤 차시 밀기, 쓰기 잠금, 2026-11-26 Codex 가 넣은 **교시 과목 바꾸기**(`supabase_schedule.replace_subject_period`) 가짜 시험 — 지금 시험 없음 | T79, T77 | `supabase_schedule.py`, `teacherlesson-schedule/server.py` | 열림 |
| P5 | (비어 있음) | 녹음·받아쓰기: 조각 재전송, 받아쓰기·수업 분석 연결, **🎤 음성 메모를 내 PC 받아쓰기로(구글 서버 안 거치게, ISSUE-053 ③ 2026-11-28 추가)** | T71(진행 중 브랜치 이어받기), T73 | `transcribe.py`, 녹음 부분 | 열림 — T71·T73 끝. 다음: 클로바노트 txt 를 받아 진도·지도서와 맞춘 수업 분석(교사 PC 의 OneDrive 수업분석 폴더에 임시 도구 있음) |

- **로컬 IDE(Codex·Antigravity)는 교사 PC 의 원래 `my-skills` 폴더에서 한 번에 하나**(교대). 받고 올리기는 `python tools/sync_work.py start/save/end`([WORKER_GUIDE 2-2](WORKER_GUIDE.md)). 클라우드 Codex·Claude 웹은 GitHub 에서 따로 일하므로 함께 돌아도 됨.
- **`web/index.html`·`assistant_server.py` 는 P1·P2 가 같이 건드린다** → 새 기능은 새 파일로, 큰 파일에는 불러오는 몇 줄만. 먼저 합쳐진 쪽 뒤에 다른 쪽이 바로 main 을 받아 맞춘다.

## K. 수업 비서 큰 일 — 체크리스트 (2026-11-27 채움, 할 수 있는 데까지 · 이어받기)

> 한 작업자가 끝까지 못 해도 된다. 체크리스트 한 칸 끝날 때마다 커밋·푸시·일지 `진행 — ①② 끝 / 다음: ③`. 토큰이 끊기면 다음 작업자가 `--next` 로 같은 브랜치를 이어받아 남은 칸부터 한다.
> 쓸 만한 중간(시험 통과)이면 일지 `합칠 준비` → PR 하고 계속. 전부 끝나면 `PR 올림`. `web/index.html`·`assistant_server.py` 는 P2(Codex)와 같이 쓰므로 **불러오는 몇 줄만**, 새 기능은 새 파일로.

| 번호 | 할 일(체크리스트) | 고칠 파일 | 끝난 기준 | 등급·상태 |
|---|---|---|---|---|
| T98 | **지난 미완료 차시 알리기·가져오기**(teacherlesson-assistant ISSUE-043 — 어제 `planned` 로 남은 차시가 오늘 화면에서 사라짐). ① `supabase_schedule.py` 에 오늘 앞 날짜의 미완료(`planned`) 슬롯을 읽는 함수(읽기만, 가짜 클라이언트 시험) ② `assistant_server.py` `state()` 응답에 `overdue` 목록(과목·차시·원래 날짜·교시) ③ 화면: 오늘 교시 위에 "지난 미완료 N개" 알림 — 새 파일 `web/overdue.js`, 차시마다 [이 교시로 가져오기] 는 기존 `과목·차시 바꾸기`(`replace_subject_period`) 확인 창을 그대로 부름. **자동으로 DB 를 바꾸지 않음** ④ `tests/test_issue_repros.py` ISSUE-043 xfail 지우고 통과 ⑤ ISSUE-043 갱신 | `supabase_schedule.py`, `assistant_server.py`(`state` 몇 줄), 새 `web/overdue.js`, `web/index.html`(불러오기 몇 줄), 시험 | ①~⑤, 전체 시험 통과 | R · 완료 |
| T99 | **클로바노트용 MP3 내보내기**(ISSUE-039, 설계 [docs/plans/clova-export.md](../skills/teacherlesson-assistant/docs/plans/clova-export.md) 그대로). ① 새 `audio_export.py` — ffmpeg 찾기(없으면 설치 안내 문장)·변환 명령 만들기(MP3 64kbps 모노)·결과 파일 이름을 순수 함수로 ② `GET /api/recording-export/<날짜>/<파일>` — 원본은 그대로 두고 변환본을 데이터 폴더에 만들어 내려줌, 이미 있으면 재사용 ③ 녹음 목록에 `🎧 클로바노트용` 단추(새 `web/recording_export.js`) ④ 가짜 ffmpeg(subprocess mock) 시험: 없음·실패·성공·재사용·경로 탈출(`..`) 막기 ⑤ ISSUE-039 에 교사 PC 확인할 것(실제 50분 녹음 변환 시간·크기) | 새 `audio_export.py`·`web/recording_export.js`, `assistant_server.py`(경로 몇 줄), 시험 | ①~⑤, 전체 시험 통과 | R · 완료(2026-11-27 합침 — 교사 PC 에서 실제 녹음 변환 확인 남음, ISSUE-039) |
| T100 | **진도 서버 쓰기 경로 오류를 JSON 으로**(teacherlesson-schedule ISSUE-005 — `/api/catch-up` 밖의 쓰기 경로 6개가 `ScheduleError` 를 500 HTML 로 냄 → 수업 비서가 "알 수 없는 오류"). ① `tests/test_server_write_routes_schedule_error.py` 의 xfail 을 하나씩 통과시키기(오류 바꾸는 곳을 함수 하나로) ② 수업 비서 쪽이 그 JSON 오류 문장을 화면에 그대로 보여 주는지 확인(안 보이면 `assistant_server.py` 의 전달 부분만) ③ ISSUE-005 🟢. 잠금(T77)은 하지 않음 | `skills/teacherlesson-schedule/server.py`, 그 시험, (필요하면) `assistant_server.py` 전달 몇 줄 | xfail 0, 전체 시험 통과 | R · 완료(2026-11-27 합침) |
| T101 | **수업 흐름 점검 도구**(T40 의 도구 부분 — 🌙 준비가 만든 `flows/*.json` 이 이상한지 기계로 먼저 봄). ① 새 `flow_check.py` 순수 함수: 단계 분 합계 ≠ 40(±5)·빈 단계·음수/0분·같은 단계명 반복·옛 `do/say/tip` 과 새 단계별 안내(ISSUE-041) 섞임·차시 목표 없음 ② 지도서 구간 글(`notebooklm/<과목>/<단원>.md`)을 주면 흐름 낱말 중 구간에 없는 비율(다른 차시 내용 섞임 의심) ③ 명령줄: `python flow_check.py <flows 폴더> [--guide <md>]` → 표로 출력, 파일은 고치지 않음 ④ 가짜 흐름 10개 이상 시험 ⑤ SKILL.md 에 사용법 두 줄 | 새 `flow_check.py`, `tests/test_flow_check.py`, `SKILL.md` | ①~⑤ — 교사 PC 실제 실행은 T103 | R · 완료 |
| T104 | **빈 차시 번호 채워 보이기**(teacherlesson-assistant ISSUE-051 — 두 시간짜리 차시는 Supabase `lesson_number` 가 비어 화면에 '차시'만). ① `supabase_schedule.py` 에 순수 함수: 같은 과목·단원 차시를 `sort_order` 로 줄 세워 빈 번호를 순서로 채움(있는 번호와 어긋나면 있는 번호를 믿고 그 뒤부터 다시 셈), 같은 제목이 이어지면 `3~4` 범위와 '몇 번째 시간' ② `day_schedule`·`upcoming` 이 그 함수를 씀 — 단원 차시 목록은 한 번 읽어 재사용(요청 수 늘리지 않게) ③ 화면에 `3~4차시 (1/2)` 처럼 ④ 가짜 시험: 국어 4단원 모양(1,2,빈×4,7,빈×6,14) → 3~6·8~13 ⑤ **DB 는 고치지 않음** | `supabase_schedule.py`, `web/index.html`(표시 몇 줄), 시험 | ①~⑤, 전체 시험 통과 | R · 완료 |
| T105 | **교실 PC 새 Chrome 창 전면 표시 고치기**(ISSUE-002·042, T102 재현): NotebookLM·수업 사이트 요청은 성공 안내가 나와도 새 창이 창 목록·전면에 안 보임. ① 공용 Chrome 프로필로 실제 새 창이 생기는지 확인 ② `wait_for_new_window`가 못 찾는 원인 기록 ③ 필요하면 `debug_port` CDP `Page.bringToFront` 연결 ④ 모니터 1대면 남는 영역, 2대면 오른쪽 모니터 배치 실제 확인 ⑤ 가짜 user32·CDP 시험 | `assistant_server.py`, `test_assistant_server.py`, ISSUE-002·042 | NotebookLM·사이트 창이 실제로 보이고 배치됨, 시험 통과 | P · 열림 |
| T102 | **교실 PC 확인 묶음**(ISSUES 에 '교실 PC 확인 대기'로 쌓인 것 한 번에): ISSUE-042(☀ 오늘 준비·🌙 내일 준비·📞 검색·오른쪽 모니터), ISSUE-046(옛 사회 기록 분리 알림), ISSUE-048(녹음 목록·재생·내려받기), ISSUE-049(바로가기 실행 때 `py` 없음 오류), ISSUE-002(NotebookLM 새 창). 하나씩 실제로 눌러 보고 ISSUES 를 🟢 또는 '남은 것 — 무엇'으로. **진도·DB 는 바꾸지 않음**(보기만), 고칠 것이 나오면 K 에 새 일로 적어 PR 설명에 | ISSUES.md(상태만) | 다섯 개 모두 🟢 또는 남은 것 적힘 | P · 완료 |
| T103 | **다음 주 수업 미리 준비 + 점검**(T43·T40 실행 부분): 다음 주 날마다 `prepare_lessons.py --date` → 실패 차시 목록 → T101 `flow_check.py` 로 만든 흐름 점검 → `데이터 폴더/reports/flow_check_<날짜>.md`(저장소 밖). 흐름은 고치지 않고, 반복되는 실패 원인을 ISSUES 에 | (코드 안 고침) ISSUES.md | 보고 파일 + 실패 원인 ISSUES 기록 | P · 열림 |
| T106 | **💬 학생 대응 멘트 도우미**(ISSUE-052 ①, 참고: 쌤동네 '학생 대응 멘트 도우미'). 수업 중 아이가 한 말·행동 단추를 누르면 교육적으로 맞는 대답 2~3개를 띄운다. **AI 호출 없이** 문장 파일만(토큰 0 원칙). ① 새 `web/ment.json` — 상황 12개 이상(떠들기·"못 해요" 포기·거부·다툼·남 탓·고자질·자리 이탈·장난·울음·무시하기·늦게 옴·과제 안 함), 상황마다 대답 2~3개 + 바탕 원리 한 줄(나-전달법, 감정 읽기, 선택권 주기, 성장 마인드셋, 행동과 사람 나누기 등) ② 새 `web/ment.js` — 오른쪽 작은 칸 또는 접는 칸, 상황 단추 → 대답 크게, 📋 복사 ③ '이번 주 집중 하나' — 교사가 고친 행동 하나를 골라 두면 칸 맨 위에 늘 보임(localStorage) ④ 교사가 자기 대답을 덧붙이면 데이터 폴더 `ment_custom.json` 에(저장소 아님) ⑤ 누른 횟수만 날짜·상황별로 세서 주간 정리에 `상황별 몇 번`(이름 없음) ⑥ 시험: json 모양 검사·custom 합치기 | 새 `web/ment.json`·`web/ment.js`, `assistant_server.py`(custom 읽기·쓰기 경로 몇 줄), `web/index.html`(불러오기 몇 줄), 시험 | ①~⑥, 전체 시험 통과 — **문장 내용은 교사 검토**(PR 설명에 표로) | R · 열림 |
| T107 | **📅 오늘·이번 주 일정과 할 일 칸**(ISSUE-052 ②, 참고: 굿데이티처 캘린더·D-day·AI 알림·할 일). 일정DB 시트(`school-todo-kakao`, 카톡 아침 알림과 같은 시트)를 **읽어** 수업 비서 위쪽에 보여 준다. ① 새 `schedule_panel.py` 순수 함수: 일정DB 행 → 오늘 행사(학교·출장·공지), 이번 주 남은 일정, 기한 있는 할 일(구분 `개인`, ✔ 없는 것) `D-n` — 규칙은 `schooltodo/message.py` 와 같게(가능하면 그 함수를 불러 씀) ② `GET /api/agenda` — 시트는 `schooltodo.db.SheetsDb.from_env()` 로 읽고 10분 캐시, 실패하면 빈 목록과 이유 ③ 새 `web/agenda.js` — 위쪽 한 줄 요약("오늘 출장 1 · 할 일 D-1 2"), 누르면 펼침 ④ ➕ 빠른 할 일: 입력하면 시트의 '빠른입력' 탭에 한 줄(다음 sync 가 일정DB 로 옮김, `schooltodo/inbox.py` 규칙) — **확인 창 뒤에만 씀** ⑤ 쉬는 시간(교시 사이)에 다음 교시 과목 + 오늘 남은 할 일 수를 '지금 할 일' 카드 아래 한 줄로 ⑥ 가짜 시트 시험 | 새 `schedule_panel.py`·`web/agenda.js`, `assistant_server.py`(경로 몇 줄), `web/index.html`(불러오기 몇 줄), 시험 | ①~⑥, 전체 시험 통과 — 실제 시트 읽기는 교사 PC 에서 | R · 열림 |
| T108 | **✅ 제출 확인표**(ISSUE-052 ③, 참고: 굿데이티처 제출 확인표). 동의서·신청서·과제를 누가 냈는지 번호 칸을 눌러 체크. ① 새 `submissions.py` — 데이터 폴더 `submissions/<제목>.json`(번호→낸 날짜), 만들기·체크·안 낸 번호 목록 순수 함수 ② `GET/POST /api/submissions` ③ 새 `web/submissions.js` — 번호 칸 표(반 인원은 config, 이름은 데이터 폴더 명단 파일이 있으면 그 PC 화면에만), 안 낸 번호 복사 단추(알림장용) ④ 저장소·서버 밖으로 보내지 않음, 화면 출력·로그에 이름 없음 ⑤ 가짜 명단 시험 | 새 `submissions.py`·`web/submissions.js`, `assistant_server.py`(경로 몇 줄), 시험 | ①~⑤, 전체 시험 통과 | R · 열림 |
| T109 | **🍱 급식·날씨 작은 칸**(ISSUE-052 ④, 참고: 굿데이티처). ① 새 `school_info.py` — 급식: NEIS 교육정보 개방 포털 급식 API(중앙 `.env` 공용 키 `NEIS_SCHOOL_CODE`·`NEIS_OFFICE_CODE`·`NEIS_API_KEY` — 교사가 넣었고 급식 조회 됨, 2026-11-28), 날씨: 키 없는 open-meteo(좌표는 `.env`) — 하루 한 번 캐시 ② `GET /api/school-info` ③ 새 `web/school_info.js` — 위쪽 오른쪽에 "🍱 오늘 메뉴 · ☀ 12°" 한 줄, 알레르기 번호는 지움 ④ 인터넷이 없으면 조용히 숨김 ⑤ 가짜 응답 시험 | 새 `school_info.py`·`web/school_info.js`, `assistant_server.py`(경로 몇 줄), 시험 | ①~⑤, 전체 시험 통과 — 실제 조회는 교사 PC(키 있음) | R · 열림 |
| T110 | **🌙 어두운 화면·칸 접기·숨기기**(ISSUE-052 ⑤, 참고: 굿데이티처 꾸미기). ① 새 `web/theme.css`·`web/layout.js` — 밝은/어두운 화면 단추, 칸(지금 할 일·사이트 목록·메모·새로 생기는 일정·멘트 칸)마다 접기·숨기기, 설정은 localStorage ② 수업 진행(🎯) 화면은 그대로 크게 ③ P2(휴대폰 화면 `mobile.css`)와 겹치지 않게 — 먼저 main 을 받고 `mobile.css` 규칙을 덮지 않는지 확인 | 새 `web/theme.css`·`web/layout.js`, `web/index.html`(불러오기 몇 줄) | 두 화면·접기·숨기기가 새로 고쳐도 유지, JS 시험 통과 | R · 열림 |
| T111 | **받아쓰기 고쳐 쓰기 사전**(ISSUE-053 ①, 참고: RamBot '자주 쓰는 말·고쳐 쓰기'). ① 데이터 폴더 `stt_words.json` — `자주 쓰는 말`(목록)·`고쳐 쓰기`(틀린 말→맞는 말). 학생 이름이 들어가므로 저장소에 넣지 않음, 저장소에는 `stt_words.example.json`(가짜 낱말) ② `transcribe.py` — faster-whisper 에 자주 쓰는 말을 힌트로(`initial_prompt`/`hotwords`, 길이 제한 지킴), 받아쓴 뒤 고쳐 쓰기 적용(낱말 경계만, 긴 것부터) ③ 수업 비서 화면 설정에 사전 고치는 칸(없으면 파일 직접) ④ 시험: 바꾸기 순서·겹침·경계, 힌트 길이 자르기 | `transcribe.py`, 새 `stt_words.example.json`, 시험 | ①~④, 전체 시험 통과 | R · 열림 |
| T112 | **수업 중 말로 명령**(ISSUE-053 ②, 참고: RamBot 명령 모드). 🎯 수업 진행 화면에서만, 단추로 켜고 끄며 **기본은 꺼짐**. ① 새 `web/voice_cmd.js` — 정해진 말만: "다음 단계"·"이전 단계"·"타이머 N분"·"좋았음"·"고칠점"·"별표"·"녹음 시작/멈춰"(비슷하게 들려도 알아듣게 낱말 표), 그 밖의 말은 버리고 글로 남기지 않음 ② 듣는 중 표시 색(명령 파랑), 알아들으면 말풍선 "다음 단계로!" ③ 브라우저 음성 인식은 소리가 구글로 간다는 안내를 켤 때 한 번 ④ 명령 해석은 순수 함수로 JS 시험 | 새 `web/voice_cmd.js`, `web/index.html`(불러오기 몇 줄), 시험 | ①~④, JS 시험 통과 | R · 열림 |

## A. 자동 시험 쓰기 (R) — 소스는 고치지 말고 `tests/` 만. 네트워크·비밀값·실제 사이트 없이 가짜(mock)로. 버그는 그 스킬 ISSUES.md 에 기록하고 시험은 xfail

| 번호 | 스킬 | 시험할 것 | 상태 |
|---|---|---|---|
| T01 | util-notebooklm | `nlm.py` split_text·page_refs·parse_pages·compact·write_source·gemini_ask 모델 바꾸기 | 완료(2026-11-25 합침) |
| T02 | teacherlesson-assistant | `prepare_lessons.py` parse_flow·parse_day·lesson_section, `build_units.py` group_lessons | 완료(2026-11-25 합침) |
| T03 | teacherlesson-guide | `auto_split.py` 검사·정규화 함수 | 완료(2026-11-25 합침) |
| T04 | teacherlesson-schedule | `server.py` 의 `/api/lessons`·`/api/catch-up` (Flask test client, schedule 함수는 가짜) | 완료(2026-11-25 합침) |
| T05 | classmanage-supabase-export | `parse_names`(JSON 배열·쉼표·공백), 학생별 나누기 | 완료(2026-11-25 합침) |
| T06 | personal-library-search | 순수 함수(검색어 정리·결과 파싱) | 완료(2026-11-25 합침) |
| T07 | util-storagemap | 순수 함수 | 완료(2026-11-25 합침) |
| T08 | util-pdf-translator | 쪽 나누기·글 정리 함수(번역 API 는 가짜) | 완료(2026-11-25 합침) |
| T09 | personal-obsidansystem-main | 노트 묶음·파일 이름 규칙 함수 | 완료(2026-11-25 합침) |
| T10 | personal-youtube-gemini-kakao-automation | 자막 정리·메시지 만들기 함수(카카오·Gemini 는 가짜) | 완료(2026-11-26 합침) |
| T11 | admin-gbetalk | 받은 쪽지 정리·파싱 함수(실제 발송 금지, 화면 조작 부분은 제외) | 완료(2026-11-26 합침) |
| T12 | personal-carrot | 순수 함수 | 완료(2026-11-25 합침) |
| T13 | workflow-hub-main / util-webtoguide / util-web-scraper | 순수 함수(각각 따로 브랜치) | 완료(2026-11-26 합침) — web-scraper 윈도우 경로·webtoguide 결과를 data_dir 로(각 PC output 백업 필요, ISSUE-004) |
| T14 | teacherlesson-workspace | `scripts/sync_semester2.py` 의 대조·변환 함수(Supabase 가짜) | 완료(2026-11-26 합침) |
| T15 | teacherlesson-from-neis | `extension/popup.js` 최상위 순수 함수(`normalizeApproverNames`·`sanitizeApprovalProfiles`·`buildApprovalBatches` 등) — Node `vm` 으로 파일을 불러오되 `document`·`chrome` 은 가짜. **NEIS 페이지에 주입되는 함수(`absence-workflow.js`, popup.js 의 `…OnNeis`) 안쪽 함수는 따로 불러올 수 없으니 대상에서 뺀다**(크롬 주입 구조상 통째로여야 함) | 완료(2026-11-26 합침) |

## B. 작은 기능·정리 코드 (R) — 각자 적힌 파일만

| 번호 | 할 일 | 고칠 파일 | 끝난 기준 | 상태 |
|---|---|---|---|---|
| T20 | 학교 PC 점검 도구 | teacherlesson-assistant `check_setup.py`, `점검_PC.bat` | 가짜 시험 통과 | 완료(2026-11-25 합침, 시험 47개) |
| T21 | 수업 메모 슈파베이스 동기화 부품 | teacherlesson-assistant `memo_sync.py`, `sql/lesson_memos.sql` | 가짜 HTTP 시험 통과 | 완료(2026-11-25 합침, 시험 24개 — 서버 연결은 T49) |
| T22 | **개인정보 검사 도구**: 커밋 전에 바뀐 줄에서 전화번호·주민번호 모양·이메일·`sk-`/`AIza` 같은 키 모양·`C:\Users\<이름>` 을 찾아 경고 | 새 `tools/check_privacy.py` + 시험 | `git diff --staged` 를 읽어 경고, 가짜 예시 시험 | 완료(2026-11-25 합침) |
| T23 | **GitHub Actions**: PR 마다 `python tools/build_catalog.py --check` + 시험이 있는 스킬 pytest(비밀값 없이 도는 것만) + T22 | 새 `.github/workflows/check.yml` | PR 에서 초록불 | 완료(2026-11-25 합침) |
| T24 | `build_catalog.py --check` 강화: SKILL.md 없는 폴더·`generated_rows`/`tmp*`/`*.pdf` 같은 결과물이 추적되면 경고 | `tools/build_catalog.py` | 기존 통과 유지 + 새 경고 시험 | 완료(2026-11-25 합침) |
| T25 | classmanage-supabase-export: 결과 엑셀을 스킬 폴더가 아니라 `data_dir()` 에 저장, `verify=False` 없애기(학생 기록이 저장소 폴더에 생김) | `export.py` | 결과 경로 시험 | 완료(2026-11-26 합침) |
| T26 | util-notebooklm `gemini_ask` 에 모델별 대기 시간 인자(작은 글은 30~45초), 결과에 쓴 모델 돌려주기(전역 `LAST_MODEL` 대신) | `nlm.py` (+ 부르는 곳 `prepare_lessons.py`, `auto_split.py` 는 인자만) | 가짜 subprocess 시험 | 완료(2026-11-26 합침) |
| T27 | teacherlesson-schedule `/api/catch-up` 동시 요청 잠금(겹치면 수업배치 전체 다시 쓰기가 덮임) | `server.py` | 두 요청 동시 시험 | 완료(2026-11-26 합침) |
| T28 | teacherlesson-assistant `supabase_schedule.py` 진도 바꾸기 동시 요청 잠금 | `supabase_schedule.py` | 가짜 시험 | 완료(2026-11-26 합침) |
| T29 | 수업 비서 서버 `/favicon.ico` 404 → 작은 아이콘 | `assistant_server.py`, `web/` | 404 없음 | 완료(2026-11-26 합침) |
| T45 | **실패 중인 시험 4개 고치기**(teacherlesson-assistant ISSUE-030): `test_supabase_schedule.py` CatchUpTest 가 옛 동작(첫 예정 슬롯, `completed` 값)을 검사함. 2026-11-24 커밋 9d2591f 에서 '실제로 할 차시 고르기'가 **요청 날짜·교시 칸으로 옮기는** 동작으로 바뀜(ISSUE-029). 새 동작에 맞게 시험을 고치고, 고른 차시 **뒤 차시들이 차시 순서대로 남는지**(앞당겨진 칸과 겹치지 않는지) 시험을 더해 확인. 코드가 틀렸으면 고치지 말고 ISSUES 에 재현 시험과 함께 기록 | `test_supabase_schedule.py` | `pytest test_supabase_schedule.py` 모두 통과 또는 xfail+기록 | 완료(2026-11-25 합침) |
| T46 | 학교 PC 점검 도구 보완(검토 🟡): ① 점검 bat 는 `py -3.13`, 수업비서 bat 는 `python` 이라 다른 Python 을 볼 수 있음 → 둘 다 검사하고 다르면 ⚠, `check_setup.py` 의 'py -3.13 을 먼저 찾아요' 안내 바로잡기 ② 5180 포트가 열려 있으면 `http://127.0.0.1:5180/` 에 실제로 물어 수업 비서인지 확인 ③ config 의 port 가 숫자가 아니어도 멈추지 않게 ④ `schedule_backend` 가 supabase 가 아닐 땐 Supabase 키 없음을 ⚠ 로 | `check_setup.py`, `점검_PC.bat`, `tests/test_check_setup.py` | 시험 추가·통과 | 완료(2026-11-25 합침) |
| T47 | 메모 동기화 부품 보완(검토 🟡): ① 내려받은 메모에 서버 `memo_key` 를 그대로 저장해 중복 판정(지금은 `at` 없는 메모가 받을 때마다 늘어남) ② CLI 출력 utf-8 ③ README·SKILL.md 에 memo_sync 사용법 절 ④ (선택) 단계 기록 step·sys·adj 를 올리지 않는 설정 | `memo_sync.py`, `tests/test_memo_sync.py`, README·SKILL 의 memo_sync 절 | 중복 재현 시험 통과 | 완료(2026-11-26 합침) |
| T49 | (교사 PC, Claude Code) 메모 동기화 연결: SQL 실행(진도와 같은 슈파베이스 프로젝트) → `save_session` 뒤 `push_session` 을 **백그라운드 스레드**로 → `실행_수업비서.bat` 에서 서버 켜기 **전에** `memo_sync.py pull --if-older 24` → 두 PC 에서 확인. **먼저 교사 결정**: 📝·🔧·🎤 같은 자유 글 메모에 학생 이름이 들어가면 그대로 슈파베이스에 올라감(🙋 학생 메모만 제외됨) | `assistant_server.py`, bat | 두 PC 메모 같음 | 교사 결정 대기 |
| T58 | 개인정보 검사 도구(`tools/check_privacy.py`) 다듬기(검토 🟡): ① 오탐 — 13자리 숫자(타임스탬프·견적번호·NEIS 코드)를 주민번호로, 영문자 붙은 숫자를 전화번호로, `setup-python@v5.1.0`·`lodash@4.17.21`·`git@github.com` 을 이메일로 잡음 — **이메일은 이제 괜찮으므로(2026-11-25 교사 결정) 이메일 검사는 뺀다** → 숫자 앞뒤 `[0-9A-Za-z]` 막기, 주민번호는 앞 6자리 날짜 확인 ② 미탐 — 노션 `ntn_`·`secret_`, 32자리 16진 DB ID, `GOCSPX-`, `/c/Users/<이름>`, `.env` 파일 자체 ③ `--stdin` 을 `sys.stdin.buffer` + `errors=replace` 로 ④ `--diff-args` 가 뒤 인자를 다 가져감, `++ ` 로 시작하는 추가 줄 빠짐. 다 되면 `.github/workflows/check.yml` 의 `--warn-only` 를 빼는 것을 PR 에 제안 | `tools/check_privacy.py`, `tests/test_check_privacy.py` | 오탐·미탐 예시 시험 통과 | 완료(2026-11-26 합침) — PR 차단 전환은 T78 뒤로 |
| T59 | 추적 중인 결과물 정리 목록(T24 경고 약 40건): exam-grader 임시 파일 42개, graderV2 PDF 2개(**학생 시험지일 수 있음**), record-trade 증권사 PDF 26개, youtube-kakao `tmp_*.vtt`, school-print `ParameterSetObject.pdf` → 스킬별로 무엇인지·지워도 되는지 표로(지우지 말 것, 교사 결정) | `docs/reviews/tracked-outputs.md` | 표 완성 | 완료(2026-11-26 합침) |

## C. 문서 정리 (R) — 정보는 빼지 말고 양식·쉬운 한국어로

| 번호 | 할 일 | 상태 |
|---|---|---|
| T30 | teacherlesson-assistant ISSUES 표준 양식·WORKLOG 겹침·SKILL/README 최신화 | 완료(2026-11-25 합침) |
| T31 | 영어 제목·문장이 섞인 SKILL.md/README.md 를 한국어로: admin-s2b-buyer, classmanage-iscream-evaluate, classmanage-student-classifier, classmanage-student-eval-generator, classmanage-student-photo-organizer, personal-record-trade (스킬마다 브랜치 따로 가능) | 완료(2026-11-26 합침) |
| T32 | teacherlesson-guide `splitter/README.md`(영어) → 한국어, 상위 SKILL.md 와 겹치는 부분 정리 | 완료(2026-11-26 합침) |
| T33 | 열린 항목이 많은 ISSUES.md 표준 양식으로: admin-neis-bot, school-todo-kakao, homepage-school-board, personal-video-note, teacherlesson-from-neis (스킬마다 따로) | 완료(2026-11-26 합침) |
| T34 | 스킬 58개 SKILL.md 앞머리 점검: description 이 "언제 쓰나"를 말하는지, summary 가 한두 문장인지, status 가 맞는지 → 고칠 목록을 `docs/reports/skill-meta-review.md` 로 (직접 고치지 말고 목록만) | 완료(2026-11-26 합침) |
| T35 | 코드가 없는 스킬(admin-buying-product, personal-attach-files, personal-free-parents-app, teacherlesson-aiep/classtool/courseware-builder 등) SKILL.md 가 실제 절차 문서로 충분한지 점검 목록 | 완료(2026-11-26 합침) |

## D. 교사 PC 에서만 (P) — Gemini CLI 작업자 등, 교사 PC 의 데이터를 씀

| 번호 | 할 일 | 상태 |
|---|---|---|
| T40 | 🌙 자동 준비로 만든 `flows/*.json` 을 같은 차시 지도서 글(`notebooklm/<과목>/<단원>.md` 구간)과 대조 → 다른 차시 내용·지도서에 없는 내용·시간 합계 이상 목록(`데이터 폴더/reports/flow_check_<날짜>.md`). 흐름은 고치지 않음 | 보류 — K T101·T103 로 옮김(2026-11-27) |
| T41 | 한 주 수업 메모(sessions)에서 출판사별로 반복되는 특징 후보 뽑기 → 교사가 골라 `publisher_notes.json` 에 | 열림 |
| T42 | `teacherlesson-guide/auto_split.py` 를 2학기 남은 단원마다 실행, 검사 실패 단원 목록 + 이유 | 열림 |
| T43 | 다음 주 수업을 `prepare_lessons.py --date` 로 하루씩 준비하고 실패 차시 목록(음악은 지도서 PDF 없음 알려진 문제) | 보류 — K T103 로 옮김(2026-11-27) |
| T44 | 미술 5·6교시 진도 확인: 슈파베이스 진도는 둘 다 '괴불주머니 만들기', 사이트는 5~6차시 '자개 무늬로 생활용품 꾸미기' → 대조표만 만들고 교사 확인 | 열림 |

## E. 문서 — 원래 T(글만) 등급이던 것. 이제 R 작업자가 저장소에 파일로 올린다(결과 파일 위치는 상태 칸)

| 번호 | 할 일 | 읽을 파일(원문 주소로) | 상태 |
|---|---|---|---|
| T50 | 수업 비서 **교사용 사용 설명서 한 장**(화면 순서대로: 날짜·교시 → 🌙 수업 준비 → 지금 할 일 → 메모 → 진도 조정). 그림 없이 쉬운 말 | teacherlesson-assistant `README.md`, `SKILL.md` | 완료(2026-11-26 합침) |
| T51 | **학교 PC 처음 설치 안내서**(Python·Node·Gemini CLI·크롬 로그인·OneDrive, 순서·확인 방법) | teacherlesson-assistant `README.md`, T20 결과 | 완료(2026-11-26 합침 — claude-web-173, `skills/teacherlesson-assistant/docs/INSTALL_SCHOOL_PC.md`) |
| T52 | 🌙 자동 준비 질문문(PROMPT) 개선안: 좋은 발문 기준(열린 질문·학생 경험 연결), 3학년 수준 말, 시간 배분 원칙을 넣은 새 문안 + 이유 | teacherlesson-assistant `prepare_lessons.py` 의 `PROMPT` | 완료(2026-11-26 합침 — claude-web-162, 개선안 `skills/teacherlesson-assistant/docs/plans/T52-prompt.md`) · 코드에 넣을지는 T97(교사 결정) |
| T53 | 수업 비서 **손으로 확인하는 점검표**(새 기능마다: 무엇을 누르면 무엇이 보여야 하는지) | teacherlesson-assistant `README.md`, `ISSUES.md` | 완료(2026-11-26 합침 — ag-1, `skills/teacherlesson-assistant/docs/checklist-manual.md`) |
| T54 | 학생 발표 메모를 누가기록으로 모을 때의 **기록 문장 원칙**(사실 위주, 평가어 피하기, 개인정보) 초안 | classmanage-student-eval-generator `SKILL.md` | 보류(묶음 밖) |
| T55 | 저장소 전체 **용어 사전**: 진도표·수업배치·차시·흐름·단원 개관·슬롯·record_key/lesson_id 등 쉬운 설명 한 줄씩 | `README.md`, teacherlesson-* SKILL.md | 완료(2026-11-26 합침) |
| T56 | `docs/SECURITY_LESSONS_LEARNED.md` 를 읽고 **작업자용 개인정보 체크리스트** 1쪽 | 그 파일, `docs/WORKER_GUIDE.md` | 완료(2026-11-26 합침) |
| T57 | 스킬 하나를 골라 SKILL.md 를 **쉬운 한국어로 다시 쓴 안**(뜻은 그대로) — 스킬마다 따로 | 고른 스킬 `SKILL.md` | 열림 · ★ 묶음 스킬만, 고친 SKILL.md 를 그대로 PR · 합침(2026-11-26, 은정): teacherlesson-schedule·teacherlesson-guide·util-notebooklm → 남은 것 teacherlesson-assistant·teacherlesson-from-neis |

## F. 2026-11-26 채움 — 시험이 찾은 버그 고치기 (R) · 각 스킬 ISSUES 에 증상이 있고, 시험은 xfail 로 표시돼 있음

> 방법: 그 스킬의 xfail 시험을 하나 골라 **소스를 고쳐** 통과시키고 xfail 표시를 지운다. 고친 범위는 그 함수만. ISSUES 항목을 🟢 로.

| 번호 | 스킬 | 할 일 | 상태 |
|---|---|---|---|
| T60 | teacherlesson-workspace | `sync_semester2.safe_int(12.0)` 이 None → `int(float(...))` (ISSUE-T14) | 완료(2026-11-26 합침) |
| T61 | classmanage-supabase-export | xfail 4개(ISSUES 참고) | 완료(2026-11-26 합침) |
| T62 | personal-carrot | xfail 6개 | 완료(2026-11-26 합침) |
| T63 | personal-library-search | xfail 2개 | 완료(2026-11-26 합침) |
| T64 | util-pdf-translator | xfail 5개 | 완료(2026-11-26 합침) |
| T65 | personal-obsidansystem-main | xfail 4개 | 완료(2026-11-26 합침) |
| T66 | personal-youtube-gemini-kakao-automation | xfail 3개 | 완료(2026-11-26 합침) |
| T67 | util-notebooklm / teacherlesson-assistant / teacherlesson-guide | 루트 `tests/` 의 xfail 6개(T01~T03) | 완료(2026-11-26 합침) |
| T68 | teacherlesson-assistant | `prepare_lessons.parse_flow`: JSON null 을 "None" 글자로 저장(ISSUE-032), 설명 글의 중괄호에 걸림(ISSUE-031) | 완료(2026-11-26 합침) |
| T69 | util-storagemap / workflow-hub-main / teacherlesson-schedule | 남은 todo·xfail(각 ISSUES) | 완료(2026-11-26 합침) |

## G. 2026-11-26 채움 — 수업 비서 새 기능 (R, 비밀값 없이 만들 수 있는 것)

| 번호 | 할 일 | 고칠 파일 | 끝난 기준 | 상태 |
|---|---|---|---|---|
| T70 | **교실 도구 묶음**: 타이머(분·초, 끝나면 화면 깜빡임), 발표자 뽑기(이번 반 번호 범위에서 무작위·중복 없이, 이름은 쓰지 않음), 소음 측정(마이크 크기 막대, 녹음·저장 안 함). 수업 비서 화면의 접는 칸 하나로 | `web/tools.js`(새), `web/index.html` 에는 칸 하나와 불러오기만 | 브라우저 없이 도는 순수 함수 시험(node) + 손 점검 순서를 README 에 | 완료(2026-11-26 합침 — ag-1, 브랜치 task/T89-classroom-tools-bundle) |
| T71 | **녹음 받아쓰기 뼈대**: `transcribe.py` — 데이터 폴더의 수업 녹음(webm)을 로컬 받아쓰기(faster-whisper 가 있으면, 없으면 안내)로 글로, `[mm:ss]` 메모와 시간 맞춰 붙이기. 분석: 교사 말 비율(받아쓰기 화자 구분이 없으면 '확인 필요'), 단계별 시간, 물음표 문장 수 | `transcribe.py`(새), 시험 | 가짜 받아쓰기 결과로 시간 맞추기·분석 시험 | 완료(2026-11-26 합침) |
| T72 | 시간이 모자랄 때 **뒤 단계를 한 번에 줄이는 단추** — 남은 단계의 분을 비례로 줄이되 '꼭 해야 함' 단계는 덜 줄임(ISSUE-009) | `web/index.html` 의 단계 시간 부분 | 줄이는 계산을 순수 함수로 빼서 시험 | 완료(2026-11-26 합침, claude-web-173) |
| T73 | 녹음 조각 하나가 저장에 실패하면 그 뒤 webm 이 재생 안 될 수 있음 → 조각 순번 확인·재전송(ISSUE-010) | `web/index.html`(녹음 부분), `assistant_server.py`(`save_audio`) | 순번 빠짐·재전송 시험 | 완료(2026-11-26 합침) |
| T74 | `실행_수업비서.bat` 이 `py -3.13` 과 `python` 을 섞어 씀 → `py -3.13` 하나로, 없으면 `python`(ISSUE-034) | `실행_수업비서.bat`, `점검_PC.bat` | `check_setup.py` 실행기 항목 ✅ | 완료(2026-11-26 합침 — Codex 의 같은 고침보다 이쪽을 씀) |
| T75 | `check_setup.py` — config.json 이 `{ }` 가 아니면 멈춤(ISSUE-035) | `check_setup.py`, 시험 | 시험 추가·통과 | 완료(2026-11-26 합침) |
| T76 | 수업 메모·🙋 학생 발표 메모를 **주간 정리 글**로: sessions 에서 과목·출판사별 고칠점·좋았음 모으기(학생 이름은 학생별 절로만, 바깥에 보내지 않음) → `데이터 폴더/reports/week-<날짜>.md`. 출판사 주의점 후보를 따로 표시 | `weekly_report.py`(새), 시험 | 가짜 sessions 로 시험 | 완료(2026-11-26 합침) |

## H. 2026-11-26 검토에서 나온 후속 일

| 번호 | 할 일 | 고칠 파일 | 끝난 기준 | 등급·상태 |
|---|---|---|---|---|
| T77 | teacherlesson-schedule: 수업배치 전체를 다시 쓰는 쓰기 경로 7개(`/api/catch-up`·`done`·push·extend·pull·move·swap)를 잠금 하나로 감싸기(지금은 catch-up 만, ISSUE-004 한계) | `server.py`, 시험 | catch-up 과 push 동시 요청 시험 | P · 열림 |
| T78 | `tools/check_privacy.py` 남은 것: ① 사용자 경로(`C:\Users\<이름>`)는 경고만, 종료 코드에서 빼기 + `…`·`...`·`xxx` 는 예시로 보기 ② 전화번호 가운데 묶음 첫 자리 `[1-9]`(NEIS 10자리 기관 코드 오탐) ③ 하이픈 없는 13자리 주민번호는 날짜 + 검증 숫자가 맞을 때만 ④ `.env` 를 `diff --git` 줄에서도 찾기, `secret_` 은 `secret_[A-Za-z0-9]{40,}` 로 좁히기. 다 되면 PR 설명에 check.yml `--warn-only` 빼기 제안(공용 파일이라 직접 고치지 말 것) | `tools/check_privacy.py`, `tests/test_check_privacy.py` | 오탐·미탐 시험 통과, 열린 브랜치 diff 에서 오탐 0 | R · 완료(2026-11-26 합침) |
| T79 | teacherlesson-assistant ISSUE-033 남은 점: 앞 차시로 따라잡아 마치면 원래 칸의 뒤 차시가 지난 날에 '예정'으로 남음. **교사 결정(2026-11-26): 뒤 차시들을 다음 칸으로 민다. 또는 따라잡기 확인 창에서 "뒤 차시를 다음 칸으로 밀까요?" 물어서 고르게** (기본은 밀기, 묻는 쪽이 쉬우면 그렇게) | `supabase_schedule.py`, `web/index.html`(확인 창), `test_supabase_schedule.py` | L1 따라잡기·완료 뒤 L2 가 다음 수업일에 나오는 시험 통과 | P · 열림 |
| T80 | util-webtoguide: 결과가 늘 같은 `guide_output.md`·`images/` 에 저장돼 다음 글이 덮어씀 → 글마다 하위 폴더(`data_dir(..., "output", <글 번호>)`) | `webtoguide.py`, 시험 | 두 글 변환 시험에서 서로 안 덮음 | R · 완료(2026-11-26 합침) |
| T81 | `tools/merge_ready.py`: 이미 다른 판으로 main 에 들어간 브랜치를 '문서·시험만'으로 보고 다시 합치려 함(2026-11-26 `feature/pure-function-tests` — ISSUES 내용이 두 번 들어갈 뻔함). 바뀐 파일마다 브랜치가 더한 줄이 main 에 이미 거의 있으면, 또는 그 TASKS 번호가 이미 `완료`면 '건너뜀(다른 판으로 합쳐짐)'으로 | `tools/merge_ready.py`, 시험 | 가짜 저장소 시험 | R · 완료(2026-11-26 합침) |

## I. 수업 비서 다음 일 (2026-11-26 채움 — 묶음 스킬 ISSUES 에서)

| 번호 | 할 일 | 고칠 파일 | 끝난 기준 | 등급·상태 |
|---|---|---|---|---|
| T82 | 차시 자료 도우미가 진도표 이름과 사이트 이름이 조금 달라도 찾게(teacherlesson-assistant ISSUE-005 셋째): 단원·차시 이름 맞추기를 **순수 함수 하나**로(공백·괄호·번호·'차시' 글자 정리 → 같음 → 포함 → 비슷함 순), 음악·사회 도우미가 같이 쓰게. 사이트를 여는 부분은 건드리지 않음 | `sites/` 아래 새 `title_match.py`, 두 도우미의 이름 찾는 부분, 시험 | 이름이 다른 예시 10개 이상 시험 통과, 기존 sites 시험 통과 | R · 완료(2026-11-27 합침 — 2차 검토·교사 결정 (나) 반영: 띄어쓰기·기호만 다르면 자동, 그 밖은 확인받고 열기) |
| T83 | `sites/` 시험을 CI 에서 돌 수 있게: `music_douclass/test_logic.py` 가 교사 PC 의 `Downloads\music.pdf` 를 읽어 시험 모으기부터 실패 → 파일이 없으면 건너뛰게(skip), 시험이 아닌 확인용 스크립트면 이름을 바꿈. 다 되면 PR 설명에 check.yml 의 teacherlesson-assistant target 에 `sites` 를 더하자고 제안(공용 파일이라 직접 고치지 말 것) | `sites/music_douclass/test_*.py` | 교사 PC 가 아닌 곳에서 `pytest sites` 통과 | R · 완료(2026-11-26 합침) — check.yml target 에 sites 더하기는 T94 |
| T84 | (설계 메모) 나이스 시간표 변경(보결·교체)을 수업 비서 교시 탭에 '변경됨'으로 보이기(ISSUE-008 둘째): `teacherlesson-from-neis` 확장이 읽는 주간학습안내 자료 모양을 코드에서 확인하고, 수업 비서로 넘기는 방법·비교 함수 이름·화면 표시 위치를 1~2쪽으로 | 새 `skills/teacherlesson-assistant/docs/plans/neis-timetable-change.md` | 파일 경로·함수 이름 수준 설계, 모르는 것은 '확인 필요' | R · 완료(2026-11-26 합침 — claude-web-소연) · 다음 T96 |
| T85 | (설계 메모) 하이클래스 알림장 자동 게시(ISSUE-008 첫째): `admin-hitalk-sender` 의 크롬 연결 방식을 읽고, 미리보기 → 교사 확인 → 게시 순서와 `/api/notice/post` 모양을 설계. **실제 게시 금지** | 새 `skills/teacherlesson-assistant/docs/plans/hiclass-notice.md` | 설계 메모 | R · 완료(2026-11-27 합침 — 설계 메모) |
| T86 | `assistant_server.py` 첫머리 설명을 지금 기본(Supabase 진도, config `schedule_backend`)에 맞게(ISSUE-023). 설명만, 코드는 그대로 | `assistant_server.py` 첫 설명 | 시험 통과 | R · 완료(2026-11-26 합침) |
| T87 | 미술 아트앤컬쳐 차시 자료 도우미(ISSUE-006): 교사 PC 크롬 9233 세션으로 e-book 단원·활동 열기. 로그인 값은 코드에 넣지 않음. 진도는 고치지 않음(T44 대조표 먼저) | 새 `sites/art_artandculture/`, `assistant_server.py` 의 `SITE_HELPERS`, `config.example.json` | 교사 PC 에서 단추로 그날 미술 차시 e-book 이 열림 | P · 열림 |
| T88 | 사회(아이스크림) '📂 차시 자료 바로 열기'를 실제로 눌러 확인하고, Enter 기다림 없이 PPT 자동 열기·창 닫기(ISSUE-005 첫째·둘째) | `sites/social_class/` | 교사 PC 에서 단추 한 번으로 PPT 가 열림 | P · 열림 |
| T89 | 🙋 학생 발표 메모를 **명단에서 이름 고르기**로(ISSUE-009 셋째), 같은 명단으로 주간 정리 글의 이름 가리기를 정확하게(ISSUE-038). **명단 위치(교사 결정 2026-11-26)**: 학교 OneDrive `%OneDriveCommercial%\95. 개인\my-skills-data\teacherlesson-assistant\학생명단.csv` (UTF-8, 열 `번호,이름`, 교사가 엑셀로 고침) — 집·학교 PC 가 같은 파일을 봄. 경로는 중앙 .env `TEACHERLESSON_ASSISTANT__ROSTER_FILE` 이 있으면 그것, 없으면 이 기본값. 파일이 없으면 지금처럼 직접 입력. **명단 내용은 저장소·시험·일지·Supabase 밖으로 보내지 않음**(시험은 `학생A`…로) | `web/index.html`, `assistant_server.py`(명단 주는 API), `weekly_report.py`, 시험 | 가짜 명단 시험 통과, 교사 PC 에서 🙋 메모에 이름 목록이 뜸 | 프로젝트 P1(ag-1) — 교실 도구는 합침, 명단에서 이름 고르기는 남음 |

## J. 2026-11-26 저녁 채움 — 합친 결과물(S5 점검·T57·T84)에서 나온 후속 일

| 번호 | 할 일 | 고칠 파일 | 끝난 기준 | 등급·상태 |
|---|---|---|---|---|
| T90 | teacherlesson-guide ISSUE-32: 분할기 기본 결과 폴더 `output/`·`pdf_splits/` 의 지도서 PDF·`groups.json` 이 `.gitignore` 에 안 막힘(저작물 올라갈 위험) → 막기 | `skills/teacherlesson-guide/.gitignore`(또는 `splitter/.gitignore`) | `git check-ignore` 로 `splitter/output/x/pdf_splits/a.pdf` 가 막힘, ISSUE-32 🟢 | R · 완료 |
| T91 | teacherlesson-guide ISSUE-33: `map_general_guides_to_sheet.py` 가 Enter 두 번이면 그 과목 기존 진도표 행을 지우고 올림 → 두 질문의 기본값을 '올리지 않기'·'지우지 않기'로 | `mapper/map_general_guides_to_sheet.py`(`confirm_upload_action`), 시험 | 입력 없이 Enter 만 치면 아무것도 안 올리는 시험(가짜 input) | R · 완료 — 교사 결정(2026-11-26): 기본값을 '올리지 않기'로 |
| T92 | teacherlesson-schedule ISSUE-6: `auto_planner.py`·`schedule.py`·`server.py` 의 깨진 한글(`?쒗듃1` 등) 되살리기. **먼저** 휴업일 날짜 칸 찾기·기본 시트 이름 시험(가짜 시트)을 만들고 고칠 것. 실제 시트 날짜 칸 위치는 모르면 '확인 필요'로 ISSUES 에 | 세 파일의 깨진 글자, `tests/` | `SHEET_NAME` 없이 `tests.test_auto_planner` 통과, 날짜가 둘째 칸인 가짜 시트에서 휴업일을 읽음 | R · 완료(2026-11-27 합침 — 검토 🟢, 남은 깨진 글자 1곳은 ISSUE-6 남은 것) |
| T93 | teacherlesson-schedule ISSUE-7: `requirements.txt` 에 `PyMuPDF` 빠짐 → 넣고, check.yml 의 schedule 칸 `extra: PyMuPDF` 를 빼자고 PR 설명에 제안(공용 파일은 직접 고치지 말 것) | `skills/teacherlesson-schedule/requirements.txt` | 요구 파일만 설치한 새 가상환경에서 서버 시험이 모이고 통과 | R · 완료 |
| T94 | CI 가 `sites/` 시험도 돌게: check.yml 의 teacherlesson-assistant `target` 을 `tests sites test_assistant_server.py test_supabase_schedule.py` 로(S5 저녁 점검·T83 남은 것). `test_music_helper` 는 selenium 이 없어 건너뜀이면 됨. **공용 파일 — 브랜치 이름에 `ci`** | `.github/workflows/check.yml` | PR 에서 teacherlesson-assistant 칸 초록불, `sites` 시험이 결과에 보임 | R · 완료 |
| T95 | `sites/music_douclass/douclass_probe.py`·`scan_music_pdf_header.py` 의 `C:\Users\user\...` 하드코딩 경로 → 명령줄 인자(없으면 사용법 안내 후 끝)로. 지우지는 않음 | 그 두 파일 | 경로 없이 실행하면 안내 후 종료 코드 2, `--help` 동작, 저장소에 사용자 경로 0 | R · 완료 |
| T96 | T84 설계 이어서: 교사 PC 에서 나이스 주간학습안내에 보결·교체가 실제로 반영되는지 확인(설계 메모의 '확인 필요') → 반영되면 비교 함수·화면 표시 구현 일을 TASKS 에 나눠 적기, 안 되면 다른 자료원 메모 | `skills/teacherlesson-assistant/docs/plans/neis-timetable-change.md` 의 '확인 필요' 칸 | 확인 결과가 메모에 적힘 + 다음 일 번호 | P · 열림 |
| T97 | T52 개선안(`docs/plans/T52-prompt.md`)을 `prepare_lessons.py` 의 `PROMPT` 에 넣기 — 교사가 개선안을 읽고 넣을 부분을 고른 뒤. 넣은 뒤 한 차시 🌙 준비로 전후 비교 | `prepare_lessons.py` 의 `PROMPT` | 같은 차시 전후 결과를 교사가 확인 | P · 결정 대기(교사가 개선안 검토) |

## S. 상시 일 — 고를 일이 없을 때 (★ 수업 비서 묶음 안에서만. 번호를 브랜치에 넣고, 대상 스킬은 `--skill` 로)

| 번호 | 할 일 | 등급 |
|---|---|---|
| S1 | **묶음 스킬에서 시험 없는 부분 하나 골라** 순수 함수 시험 쓰기(위 A 묶음 방식). 고른 스킬 이름을 브랜치에 넣기: `task/S1-<스킬>` | R |
| S2 | **다른 작업자 PR 검토**: 시험 돌려 보고, 개인정보·범위 밖 수정·버그를 `docs/reviews/<브랜치>.md` 에 적어 PR 로(그 브랜치는 고치지 않음) | R |
| S3 | **묶음 스킬 ISSUES.md 열린 항목 하나 골라 재현 시험 만들기**(고치지는 말고 xfail 로) | R |
| S4 | 묶음 스킬 하나 골라 SKILL.md·README 가 코드와 맞는지 확인, 틀린 설명만 고침 | R |
| S5 | `python tools/build_catalog.py --check`·전체 시험을 돌려 깨진 것을 `docs/reviews/health-<날짜>.md` 로 | R |
| S7 | 묶음 스킬 ISSUES 📌 백로그 항목 하나를 골라 "어떻게 만들면 될지" 짧은 설계 메모(파일 경로·함수 이름 수준) → `docs/plans/` | R |

## 원래 큰 계획 (교사 PC 의 Claude Code 가 함 — 참고)

- 학교 PC 공용: 글(md)·흐름·설정은 OneDrive, PDF 는 집 PC, 녹음은 PC 에만 (teacherlesson-assistant ISSUES "지금 상태와 남은 일" 0번)
- 🙋 학생 메모 → 학생 기록 표(슈파베이스) — 표 이름·명단 출처 확인 필요
- 미술 아트앤컬쳐 e-book 차시 자동 열기, 하이클래스 알림장 자동 게시, 나이스 시간표 변경 표시, 녹음 받아쓰기
