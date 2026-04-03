# Teacher Schedule

구글 시트를 실제 운영 데이터로 사용해 교사의 수업 진도와 수업 일정을 함께 관리하는 도구입니다.

현재 구조의 핵심은 `진도표`와 `수업배치`를 분리한 점입니다.

- `진도표`: 무엇을 가르칠지 관리
- `수업배치`: 언제, 몇 교시에 가르칠지 관리
- `lesson_id`: 두 시트를 연결하는 고정 키

날짜와 교시의 진실 원천은 `수업배치`입니다.  
`진도표`의 `계획일`, `계획교시`는 브릿지 결과를 보여 주는 표시용 컬럼으로 사용합니다.

## 포함 범위

- `schedule.py`: CLI 조회, 완료 처리, 차시 연장, 날짜 밀기
- `bridge_sheet.py`: `수업배치` 생성/재동기화
- `auto_planner.py`: 시간표/휴업일/수업시작일 기반 자동 배치
- `server.py`, `src/`: 웹 UI

아래 작업은 이 저장소의 범위 밖입니다.

- 지도서 PDF 분할
- 지도서 내용을 시트 행으로 매핑/업로드

별도 저장소:

- `C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\teacher-guide-sheet-mapper`

## 시트 구조

기본 진도 시트는 `.env`의 `SHEET_PROGRESS`를 우선 사용하고, 없으면 `SHEET_NAME`을 사용합니다.

### 진도표 권장 컬럼

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

### 보조 시트

- `기초시간표`
- `휴업일`
- `수업시작일`
- `수업배치`

### 수업배치 컬럼

- `slot_date`
- `slot_period`
- `slot_order`
- `과목`
- `lesson_id`
- `status`
- `source`
- `memo`

## 현재 동작

브릿지 시트가 있으면 아래 기능은 `수업배치`를 기준으로 동작합니다.

- 오늘 / 내일 / 이번 주 / 다음 주 조회
- 과목별 다음 차시
- 수업 완료 처리
- 날짜 밀기
- 차시 연장
- 웹 UI 대시보드

완료 처리는 `lesson_id` 전체를 한 번에 닫지 않고, 해당 슬롯만 `done`으로 바꿉니다.  
같은 `lesson_id`가 연장으로 여러 슬롯에 배치되어 있다면 마지막 슬롯까지 완료되어야 `진도표.실행여부`도 완료로 바뀝니다.

## 설치

```bash
pip install -r requirements.txt
```

프런트엔드까지 사용할 경우:

```bash
npm install
```

## 주요 명령

### CLI

```bash
python schedule.py
python schedule.py lesson-ids
python schedule.py today
python schedule.py tomorrow
python schedule.py thisweek
python schedule.py nextweek
python schedule.py next
python schedule.py progress
python schedule.py done 국어 2026-04-03
python schedule.py push 국어 7 2026-04-03
```

`python schedule.py lesson-ids`는 `lesson_id` 컬럼이 없으면 추가하고, 비어 있는 행에 순차 ID를 채웁니다.

### 브릿지 시트 재동기화

```bash
python bridge_sheet.py
```

이 명령은 현재 진도표를 기준으로 `수업배치`를 다시 쓰고, 가장 이른 슬롯을 `계획일`/`계획교시`에 반영합니다.

### 자동 배치

```bash
python auto_planner.py
python auto_planner.py --mode initial --start-date 3.2
python auto_planner.py --mode fill-blanks --start-date 2026-03-02
```

- `initial`: 기존 계획일을 무시하고 전체를 다시 배치
- `fill-blanks`: 미완료이면서 계획일이 비어 있는 행만 채움

## 웹 UI

```bash
python server.py
npm run dev
```

현재 UI는 3개 탭으로 나뉩니다.

- `수업배치`: 오늘/내일/다음 주 슬롯 중심 보기
- `진도표`: 과목별 다음 차시, 단원 진행률 보기
- `관리`: 날짜 밀기, 차시 연장

## 권장 작업 순서

### 진도표 내용/순서를 바꿨을 때

1. `진도표`를 수정
2. 필요하면 `python schedule.py lesson-ids`
3. `python bridge_sheet.py`로 재동기화
4. 자동 배치가 필요하면 `python auto_planner.py`

### 운영 중 일정만 조정할 때

- CLI의 완료/밀기/연장 기능 사용
- 또는 웹 UI의 `수업배치` / `관리` 탭 사용

## 테스트

```bash
python -m unittest tests.test_schedule tests.test_auto_planner tests.test_bridge_sheet
python -m py_compile schedule.py auto_planner.py bridge_sheet.py server.py
```

프런트 빌드 확인:

```bash
npm run build
```

## 참고 문서

- [bridge-sheet-design.md](C:/Users/user/.gemini/antigravity/scratch/repos/my-skills/skills/teacher-schedule/docs/bridge-sheet-design.md)
