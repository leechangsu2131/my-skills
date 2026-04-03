---
name: teacher-schedule
description: "Google Sheets 기반 교사 수업 관리 스킬. schedule.py, bridge_sheet.py, auto_planner.py, server.py, src/를 함께 다루며 진도표와 수업배치 시트를 분리해 유지한다."
---

# Teacher Schedule Skill

이 스킬은 교사 수업 진도와 실제 수업 배치를 함께 관리하는 저장소를 다룰 때 사용합니다.

## 범위

포함:

- `schedule.py`
- `bridge_sheet.py`
- `auto_planner.py`
- `server.py`
- `src/`
- `README.md`
- `tests/test_schedule.py`
- `tests/test_server.py`
- `tests/test_auto_planner.py`
- `tests/test_bridge_sheet.py`

제외:

- 지도서 PDF 분할
- 지도서 내용을 다른 시트 행으로 매핑하는 별도 도구

관련 별도 저장소:

- `C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\teacher-guide-sheet-mapper`

## 현재 아키텍처

핵심 개념:

- `진도표`: 무엇을 가르칠지 관리
- `수업배치`: 언제, 몇 교시에 가르칠지 관리
- `lesson_id`: 두 시트를 연결하는 고정 키

우선 원칙:

- 브릿지 시트가 있으면 날짜/교시는 `수업배치`를 기준으로 본다.
- 진도표의 `계획일`, `계획교시`는 브릿지 결과가 동기화된 표시 컬럼이다.
- `lesson_id`는 `_row`보다 우선하는 식별자다.

## 사용자 관점에서 반드시 유지할 의미

### 완료 처리

- 완료한 수업은 UI에서 사라지지 않고 `완료됨`으로 남아야 한다.
- 같은 `lesson_id`가 여러 슬롯에 걸쳐 있으면 마지막 planned 슬롯까지 끝나야 진도표 완료로 본다.

### 빠른 조정 의미

빠른 조정은 하루 안 교시 순서를 바꾸는 기능이 아니다.

- `다음 차시 당겨오기`
  - 현재 슬롯 자리에 같은 과목의 다음 수업을 당겨온다.
  - 뒤쪽 같은 과목 수업들이 한 칸씩 앞으로 당겨진다.
- `이 수업 한 차시 더`
  - 현재 수업이 다음 같은 과목 시간까지 이어지도록 1차시를 더 확보한다.
  - 뒤쪽 같은 과목 수업들이 한 칸씩 뒤로 밀린다.
- `과목 전체 뒤로 밀기`
  - 특정 날짜 이후의 해당 과목 예정 수업을 일괄 이동한다.
- `교환`
  - 필요할 때만 두 슬롯의 날짜/교시를 바꾼다.

### 주간 보드

- 주간 보드는 `이번주` 고정이 아니라 선택 가능한 주를 기준으로 그려진다.
- 이전주 / 이번주 / 다음주 / 특정 날짜 선택이 가능해야 한다.
- 월간 보드는 선택한 주가 속한 달을 기준으로 같이 갱신된다.

## 수정 우선순위

1. `schedule.py`
2. `server.py`
3. `src/hooks/useScheduleData.js`
4. `src/components/`
5. 테스트
6. `README.md`

## 작업 원칙

- 브릿지 시트가 있을 때는 브릿지 기준으로 동작을 설계한다.
- 진도표 본문 컬럼과 브릿지 슬롯 컬럼을 혼동하지 않는다.
- 날짜/교시를 직접 진도표에만 수정하는 것보다 브릿지 갱신 경로를 우선한다.
- UI 문구를 바꿀 때는 실제 동작 의미도 함께 맞는지 확인한다.
- README와 SKILL 문서는 현재 구현 의미와 같아야 한다.

## 함께 바꿔야 하는 파일

### `schedule.py`를 바꿀 때

- `tests/test_schedule.py`
- 필요하면 `server.py`
- 필요하면 `src/hooks/useScheduleData.js`

### `server.py`를 바꿀 때

- `src/hooks/useScheduleData.js`
- 필요하면 `src/components/`
- 필요하면 `tests/test_server.py`

### `bridge_sheet.py`를 바꿀 때

- `tests/test_bridge_sheet.py`
- `schedule.py`
- 필요하면 `docs/bridge-sheet-design.md`

### `auto_planner.py`를 바꿀 때

- `tests/test_auto_planner.py`
- 필요하면 `bridge_sheet.py`

### UI를 바꿀 때

- `server.py`
- `src/hooks/useScheduleData.js`
- `src/components/`
- 필요하면 `README.md`

## 자주 쓰는 검증

```powershell
python -m unittest tests.test_schedule tests.test_server tests.test_auto_planner tests.test_bridge_sheet
python -m py_compile schedule.py auto_planner.py bridge_sheet.py server.py
npm.cmd run build
```

## 자주 쓰는 명령

```powershell
python schedule.py
python schedule.py today
python schedule.py nextweek
python schedule.py next
python schedule.py progress

python bridge_sheet.py

python auto_planner.py --mode initial --start-date 2026-03-02
python auto_planner.py --mode fill-blanks --start-date 2026-03-02

실행_교사일정_UI.bat
```

## 참고 문서

- [bridge-sheet-design.md](C:/Users/user/.gemini/antigravity/scratch/repos/my-skills/skills/teacher-schedule/docs/bridge-sheet-design.md)
