---
name: teacher-schedule
description: "구글시트 기반 수업 진도 관리 도구를 유지보수할 때 사용하는 작업 안내서입니다. schedule.py, auto_planner.py, map_guides_to_sheet.py를 우선 다룹니다."
---

# Teacher Schedule Skill

이 저장소는 웹 UI보다 파이썬 스크립트가 중심입니다.  
작업할 때는 아래 우선순위를 기준으로 판단합니다.

1. `schedule.py`
2. `auto_planner.py`
3. `map_guides_to_sheet.py`
4. `map_general_guides_to_sheet.py`
5. `server.py`, `schedule_app.jsx`

## 핵심 전제

- 실제 운영 데이터 소스는 Google Sheets다.
- 엑셀 파일은 구조를 이해하기 위한 참고 자료일 뿐이다.
- 사용자 입장에서는 서버/리액트보다 스케줄 파이썬 로직이 더 중요할 가능성이 높다.

## 시트 규칙

### 진도표 시트

- 기본 시트명은 `시트1`
- `과목`, `계획일`은 헤더가 있어야 한다.
- `실행여부`는 헤더가 없어도 F열이면 실행여부 열로 간주한다.
- 체크박스 열을 권장한다.
- `'true`, `'false`처럼 작은따옴표가 붙은 값도 읽을 때는 보정한다.
- 쓸 때는 문자열보다 실제 불리언을 우선 사용한다.

### 시간표/휴업일/수업시작일

- `기초시간표`: 같은 날 같은 과목이 여러 번 있으면 그대로 여러 번 배정해야 한다.
- `휴업일`: 자동 배정에서 제외한다.
- `수업시작일`: 과목별 시작일이 다를 수 있다.

## 스크립트별 작업 메모

### `schedule.py`

- 오늘/내일/이번 주/다음 주 조회를 담당한다.
- 완료 처리, 차시 연장, 일정 밀기를 담당한다.
- 차시 연장은 새 행을 만들지 않는다.
- 연장 정보는 `비고`의 `[연장일정:...]` 형식과 `연장횟수`로 관리한다.
- 같은 과목의 뒤 차시 날짜를 밀어야 한다.

수정 시 주의:

- `실행여부` 헤더가 없어도 F열 fallback을 깨지 않게 유지한다.
- 시트 읽기는 행별 API 호출 대신 한 번에 읽는 방식을 유지한다.
- 체크박스 열에는 가능하면 `True`, `False`를 쓴다.

### `auto_planner.py`

- `initial`과 `fill-blanks` 두 모드를 유지한다.
- 학기 시작일 기본값은 현재 연도 `3.2`다.
- `3.2`, `3/2`, `3-2` 입력을 허용한다.
- 과목별 수업시작일을 우선 반영한다.
- `대단원`이 숫자로 시작하지 않는 행은 자동 배정에서 제외한다.

수정 시 주의:

- 시간표 중복 과목 배정을 유지한다.
- F열 실행여부 fallback을 `schedule.py`와 다르게 해석하지 않도록 맞춘다.

### `map_guides_to_sheet.py`

- 국어와 도덕 기본 행 생성/업로드를 담당한다.
- 업로드 시 `실행여부`는 문자열 `"FALSE"`보다 불리언 `False`를 우선 사용한다.
- F열 헤더가 비어 있어도 6열이면 실행여부 열로 본다.

국어 파싱 규칙:

- `대단원`: 큰 단원명
- `소단원`: 가능하면 별도 열에 저장
- `수업내용`: 상세 차시 페이지 왼쪽 상단의 학습목표
- `차시`: 학습목표에 대응하는 실제 범위

예:

- `대단원`: `1. 생생하게 표현해요`
- `소단원`: `감각적 표현의 재미를 느끼며 시 감상하기`
- `차시`: `2(2~3)`
- `수업내용`: `감각적 표현을 이해할 수 있다.`

### `map_general_guides_to_sheet.py`

- 기타 교과용 범용 매핑 스크립트다.
- 같은 구글시트와 같은 `.env`를 사용한다.
- 기본 preset은 수학, 사회, 과학, 음악, 미술, 체육, 영어, 실과다.
- 먼저 연간 지도 계획 PDF를 찾고, 없으면 휴리스틱으로 생성한다.

수정 시 주의:

- `map_guides_to_sheet.py`의 국어/도덕 전용 로직과 섞지 않는다.
- 범용 로직은 과목별 편차가 크므로 미리보기 기준을 유지한다.
- 새 과목을 추가할 때는 preset과 테스트를 함께 고친다.

## 문서/코드 수정 시 권장 흐름

1. 먼저 `README.md`와 현재 코드가 맞는지 확인한다.
2. 시트 구조 가정이 바뀌면 `README.md`와 `SKILL.md`를 함께 고친다.
3. 스케줄 로직을 바꾸면 `tests/test_schedule.py`를 같이 본다.
4. 자동 배정 규칙을 바꾸면 `tests/test_auto_planner.py`를 같이 본다.
5. 국어/도덕 파서를 바꾸면 `tests/test_map_guides_to_sheet.py`를 같이 본다.

## 자주 쓰는 명령

```bash
python schedule.py
python schedule.py today
python schedule.py thisweek
python schedule.py done 국어 2026-03-26

python auto_planner.py --mode initial --start-date 3.2
python auto_planner.py --mode fill-blanks

python map_guides_to_sheet.py
python map_guides_to_sheet.py --upload

python -m unittest discover -s tests -v
python -m py_compile schedule.py auto_planner.py map_guides_to_sheet.py
```

## 문서에 꼭 남겨야 하는 사항

문서를 수정할 때 아래 내용이 빠지지 않도록 한다.

- Google Sheets가 운영 데이터라는 점
- `실행여부` 헤더가 없어도 F열 fallback을 쓴다는 점
- 차시 연장은 새 행 추가가 아니라 날짜 이동이라는 점
- 자동 배정의 `initial` / `fill-blanks` 차이
- 국어는 `대단원 / 소단원 / 학습목표 / 실제 차시범위` 구조라는 점
- 범용 지도서 매핑은 `map_general_guides_to_sheet.py`로 분리되었다는 점
