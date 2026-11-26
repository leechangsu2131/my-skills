---
name: teacher-schedule
description: "옛 Google Sheets 방식의 수업 진도·수업 배치 도구. 진도표(무엇을 가르칠지)와 수업배치(언제 가르칠지) 시트를 나눠 관리한다. 이 폴더의 schedule.py·bridge_sheet.py·auto_planner.py·server.py·src/ 를 보거나 고칠 때, 완료 처리·당겨오기·한 차시 더·뒤로 밀기·교환의 뜻을 확인할 때 사용한다."
metadata:
  category: 수업·교사 도구
  status: 운영
  version: v1.0.0
  summary: Google Sheets 기반 교사 수업 진도·수업 배치 관리와 자동 시간표 계획 기능을 다룬다.
---

# 교사 수업 진도 관리 (옛 Google Sheets 방식)

수업 진도와 실제 수업 배치를 함께 관리하는 이 폴더의 코드를 다룰 때 사용합니다.

## 먼저 알아 둘 것: 수업 비서와의 관계

- 수업 비서(`teacherlesson-assistant`)의 진도 원본은 이제 **Supabase**(인터넷 데이터베이스)입니다.
- 수업 비서가 이 폴더의 서버(`server.py`)를 부르는 것은 설정 `schedule_backend` 값이 `supabase` 가 **아닐 때**뿐입니다(값이 없으면 `supabase`).
- 이 폴더의 화면(React)은 아직 Google Sheets 를 봅니다. 수업 비서 화면과 헷갈리지 않습니다.
- 다만 `schedule.py` 의 일부 함수는 지금도 다른 스킬이 가져다 씁니다. 특히 `resolve_pdf_path()`(지도서 PDF 위치 찾기)는 수업 비서가 Supabase 방식일 때도 씁니다.

## 다루는 범위

포함:

- `schedule.py` — 진도 조회와 조정
- `bridge_sheet.py` — 수업배치 시트 만들기·맞추기
- `auto_planner.py` — 시간표에 따라 날짜 자동 배치
- `server.py` — 화면이 부르는 서버(Flask)
- `src/` — 화면(React)
- `README.md`
- `tests/test_schedule.py`
- `tests/test_server.py`
- `tests/test_server_lessons_catchup.py`
- `tests/test_auto_planner.py`
- `tests/test_bridge_sheet.py`

제외:

- 지도서 PDF 나누기
- 지도서 내용을 다른 시트 행에 연결하는 별도 도구

관련 다른 스킬 폴더:

- `skills/teacherlesson-guide` — 지도서 받기·나누기·진도표 행 만들기(옛 guide-splitter·guide-mapper)

## 현재 아키텍처 (자료를 나누는 방식)

| 말 | 뜻 |
|---|---|
| `진도표` | **무엇을** 가르칠지 적는 시트 |
| `수업배치` | **언제, 몇 교시에** 가르칠지 적는 시트. 코드에서는 '브릿지 시트'(두 자료를 잇는 시트)라고도 부름 |
| `lesson_id` | 두 시트를 잇는, 바뀌지 않는 번호 |

우선 원칙:

- 수업배치 시트가 있으면 날짜·교시는 **수업배치**를 기준으로 봅니다.
- 진도표의 `계획일`, `계획교시` 칸은 수업배치 결과를 옮겨 적어 보여 주는 칸입니다.
- 수업을 가리킬 때는 행 번호(`_row`)보다 `lesson_id` 를 먼저 씁니다.

## 화면에서 꼭 지켜야 하는 뜻

### 완료 처리

- 완료한 수업은 화면에서 사라지지 않고 `완료됨`으로 남아야 합니다.
- 같은 `lesson_id` 가 여러 칸에 걸쳐 있으면, 마지막 예정(`planned`) 칸까지 끝나야 진도표에서도 완료로 봅니다.

### 빠른 조정 의미

빠른 조정은 **하루 안에서 교시 순서를 바꾸는 기능이 아닙니다.**

- `다음 차시 당겨오기`
  - 지금 칸에 같은 과목의 다음 수업을 당겨옵니다.
  - 뒤에 있는 같은 과목 수업들이 한 칸씩 앞으로 옵니다.
- `이 수업 한 차시 더`
  - 지금 수업이 다음 같은 과목 시간까지 이어지도록 1차시를 더 잡습니다.
  - 뒤에 있는 같은 과목 수업들이 한 칸씩 뒤로 밀립니다.
- `과목 전체 뒤로 밀기`
  - 정한 날짜부터(그날 포함) 그 과목의 예정 수업을 한꺼번에 옮깁니다.
- `교환`
  - 필요할 때만 두 칸의 날짜·교시를 맞바꿉니다.

### 주간 보드

- 주간 보드는 `이번주`로 고정하지 않고, 고른 주를 기준으로 보여 줍니다.
- 이전주 / 이번주 / 다음주 / 특정 날짜를 고를 수 있어야 합니다.
- 월간 보드는 고른 날짜가 속한 달로 함께 바뀝니다.

## 고칠 때 먼저 볼 순서

1. `schedule.py`
2. `server.py`
3. `src/hooks/useScheduleData.js`
4. `src/components/`
5. 시험(`tests/`)
6. `README.md`

## 작업 원칙

- 수업배치 시트가 있을 때는 수업배치를 기준으로 동작을 설계합니다.
- 진도표의 칸과 수업배치의 칸을 헷갈리지 않습니다.
- 날짜·교시는 진도표만 직접 고치지 말고, 수업배치를 갱신하는 길로 바꿉니다.
- 화면의 글을 바꿀 때는 실제 동작의 뜻과도 맞는지 확인합니다.
- `README.md` 와 이 문서는 지금 코드의 동작과 같아야 합니다.

## 함께 바꿔야 하는 파일

| 바꾸는 파일 | 함께 확인할 파일 |
|---|---|
| `schedule.py` | `tests/test_schedule.py`, 필요하면 `server.py`·`src/hooks/useScheduleData.js`. 다른 스킬이 가져다 쓰는 함수면 그 스킬도 |
| `server.py` | `src/hooks/useScheduleData.js`, 필요하면 `src/components/`·`tests/test_server.py`·`tests/test_server_lessons_catchup.py`. 주소·응답 모양을 바꾸면 수업 비서의 `assistant_server.py`·`prepare_lessons.py` 도 |
| `bridge_sheet.py` | `tests/test_bridge_sheet.py`, `schedule.py`, 필요하면 `docs/bridge-sheet-design.md` |
| `auto_planner.py` | `tests/test_auto_planner.py`, 필요하면 `bridge_sheet.py` |
| 화면(`src/`) | `server.py`, `src/hooks/useScheduleData.js`, `src/components/`, 필요하면 `README.md` |

## 확인(검증) 명령

이 폴더에서 실행합니다.

```powershell
python -m unittest tests.test_schedule tests.test_server tests.test_server_lessons_catchup tests.test_auto_planner tests.test_bridge_sheet
python -m py_compile schedule.py auto_planner.py bridge_sheet.py server.py
npm.cmd run build
```

- 서버 시험에는 PDF 라이브러리 PyMuPDF(`fitz`)도 필요합니다(`requirements.txt` 에는 빠져 있음 — [ISSUES.md](ISSUES.md)).
- `test_auto_planner` 시험 1개는 알려진 실패입니다([ISSUES.md](ISSUES.md) ISSUE-003).

## 자주 쓰는 명령

실제 Google Sheets 에 연결합니다. `bridge_sheet.py`·`auto_planner.py` 를 돌리거나, 메뉴나 `schedule.py done`·`push` 로 조정하면 **시트 내용이 바뀝니다.**

```powershell
python schedule.py            # 메뉴 열기
python schedule.py today      # 오늘 수업
python schedule.py nextweek   # 다음 주 수업
python schedule.py next       # 과목별 다음 수업
python schedule.py progress   # 진도 현황

python bridge_sheet.py        # 수업배치 시트를 다시 만들어 맞춤

python auto_planner.py --mode initial --start-date 2026-03-02       # 전체를 처음부터 배치
python auto_planner.py --mode fill-blanks --start-date 2026-03-02   # 날짜가 빈 미완료 수업만 채움

.\실행_교사일정_UI.bat         # 화면 켜기 (http://127.0.0.1:5173)
```

## 참고 문서

- [bridge-sheet-design.md](docs/bridge-sheet-design.md) — 수업배치 시트 설계안
- [README.md](README.md) — 설치·화면 설명
- [ISSUES.md](ISSUES.md) — 문제·해결 기록, 할 일
