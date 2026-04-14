# Teacher Schedule

Google Sheets 기반으로 초등 수업 진도와 실제 수업 배치를 함께 관리하는 도구입니다.

이 저장소는 진도표와 실제 배치표를 분리해서 다룹니다.

- `진도표`: 무엇을 가르칠지 관리
- `수업배치`: 언제, 몇 교시에 가르칠지 관리
- `lesson_id`: 두 시트를 연결하는 고정 키

## 핵심 구조

### 1. 진도표

권장 컬럼:

- `lesson_id`
- `수업내용`
- `과목`
- `대단원`
- `차시`
- `실행여부`
- `계획일`
- `계획교시`
- `pdf파일`
- `시작페이지`
- `끝페이지`
- `비고`
- `연장횟수`

### 2. 수업배치 시트

컬럼:

- `slot_date`
- `slot_period`
- `slot_order`
- `과목`
- `lesson_id`
- `status`
- `source`
- `memo`

브릿지 시트가 있으면 날짜와 교시의 실제 기준은 `수업배치`입니다.  
진도표의 `계획일`, `계획교시`는 브릿지 결과가 동기화되어 보이는 표시 컬럼으로 사용됩니다.

## 현재 동작

### 완료 처리

- 완료한 수업은 UI에서 사라지지 않습니다.
- 같은 카드 자리에 남아 `완료됨` 상태로 보입니다.
- 같은 `lesson_id`가 여러 배치 슬롯에 걸쳐 있으면 마지막 planned 슬롯까지 끝나야 진도표의 `실행여부`가 완료로 바뀝니다.

### 수업 조정 의미

빠른 조정은 하루 안 교시 순서를 바꾸는 기능이 아닙니다.

- `다음 차시 당겨오기`
  - 현재 수업 자리에 같은 과목의 다음 수업을 당겨옵니다.
  - 뒤쪽 같은 과목 수업들이 한 칸씩 앞으로 당겨집니다.
  - 빨리 끝난 현재 차시는 상황에 따라 완료 처리됩니다.
- `이 수업 한 차시 더`
  - 현재 수업이 다음 같은 과목 시간까지 이어지도록 1차시를 더 확보합니다.
  - 뒤쪽 같은 과목 수업들이 한 칸씩 뒤로 밀립니다.
- `과목 전체 뒤로 밀기`
  - 특정 날짜 이후의 해당 과목 예정 수업을 일괄로 뒤로 미룹니다.
- `두 수업 교환`
  - 필요할 때만 두 슬롯의 날짜/교시를 바꿉니다.

## UI

실행 파일:

```powershell
실행_교사일정_UI.bat
```

처음 1회 준비:

```powershell
python -m pip install -r requirements.txt
npm.cmd install
```

직접 실행:

```powershell
python server.py
npm.cmd run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

브라우저 주소:

- 프런트: `http://127.0.0.1:5173`
- 백엔드: `http://127.0.0.1:5000`

### 화면 구성

- `수업 배치`
  - 오늘
  - 다음 수업일
  - 선택한 주의 월~금 보드
  - 선택한 달 달력
  - 이전주 / 이번주 / 다음주 / 특정 날짜 선택
- `진도 현황`
  - 과목별 다음 수업
  - 남은 수업 흐름
  - 최근 완료 기록
- `일정 관리`
  - 과목 전체 뒤로 밀기
  - 현재 수업 한 차시 더
  - 다음 차시 당겨오기
  - 슬롯 교환

## 주요 파일

- `schedule.py`: 진도표/브릿지 기준 조회와 조정 로직
- `bridge_sheet.py`: 수업배치 시트 생성과 동기화
- `auto_planner.py`: 시간표/시작일 기준 자동 배치
- `server.py`: Flask API
- `src/`: React UI
- `tests/test_schedule.py`
- `tests/test_server.py`

별도 저장소:

- `C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\teacher-guide-sheet-mapper`

## 설치

```powershell
python -m pip install -r requirements.txt
npm.cmd install
```

## 주요 명령

### lesson_id 보정

```powershell
python schedule.py lesson-ids
```

`lesson_id` 컬럼이 없으면 추가하고, 비어 있는 행에 순차 ID를 채웁니다.

### 브릿지 시트 동기화

```powershell
python bridge_sheet.py
```

현재 진도표 기준으로 `수업배치`를 다시 쓰고, 가능한 경우 진도표의 `계획일`, `계획교시`를 함께 동기화합니다.

### 자동 배치

```powershell
python auto_planner.py
python auto_planner.py --mode initial --start-date 2026-03-02
python auto_planner.py --mode fill-blanks --start-date 2026-03-02
```

- `initial`: 기존 계획일을 무시하고 전체를 다시 배치
- `fill-blanks`: 미완료이면서 계획일이 빈 행만 채움

### 기본 CLI

```powershell
python schedule.py
python schedule.py today
python schedule.py tomorrow
python schedule.py thisweek
python schedule.py nextweek
python schedule.py next
python schedule.py progress
python schedule.py done 국어 2026-04-03
python schedule.py push 국어 7 2026-04-03
```

## 권장 작업 순서

### 진도표 내용을 바꿨을 때

1. 진도표 수정
2. 필요하면 `python schedule.py lesson-ids`
3. `python bridge_sheet.py`
4. 자동 재배치가 필요하면 `python auto_planner.py`

### 운영 중 배치만 조정할 때

- UI에서 `다음 차시 당겨오기`, `이 수업 한 차시 더`, `교환`, `과목 전체 뒤로 밀기` 사용
- 또는 CLI의 완료/밀기 기능 사용

## 테스트

```powershell
python -m unittest tests.test_schedule tests.test_server tests.test_auto_planner tests.test_bridge_sheet
python -m py_compile schedule.py auto_planner.py bridge_sheet.py server.py
npm.cmd run build
```

## 참고 문서

- [bridge-sheet-design.md](C:/Users/user/.gemini/antigravity/scratch/repos/my-skills/skills/teacher-schedule/docs/bridge-sheet-design.md)
