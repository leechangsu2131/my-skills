# Teacher Schedule

구글시트를 실제 운영 데이터 소스로 사용하는 수업 진도/계획일 관리 도구입니다.  
핵심은 파이썬 스크립트 3개입니다.

- `schedule.py`: 오늘/내일/이번 주 수업 조회, 완료 처리, 차시 연장, 일정 밀기
- `auto_planner.py`: 기초시간표, 휴업일, 수업시작일을 바탕으로 계획일 자동 배정
- `map_guides_to_sheet.py`: 국어/도덕 지도서를 읽어 진도표 기본 행을 생성하고 시트에 업로드
- `map_general_guides_to_sheet.py`: 기타 교과용 범용 지도서 매핑
- `server.py`: 구글 시트 데이터를 계층형 트리(Tree) 구조로 응답하는 Flask 백엔드 API
- `src/`: TailwindCSS와 단위 컴포넌트(Dashboard, LessonList, Actions)로 모듈화된 React(Vite) 프론트엔드

## 현재 동작 요약

- 데이터 원본은 항상 Google Sheets입니다.
- `실행여부` 헤더가 없어도 F열을 실행여부 열로 간주합니다.
- F열은 체크박스 열을 권장합니다.
- `'true`, `'false`처럼 작은따옴표가 붙은 값도 읽을 때는 보정합니다.
- 쓸 때는 문자열 `"TRUE"`, `"FALSE"` 대신 실제 불리언 `True`, `False`를 쓰도록 맞춰져 있습니다.
- 차시 연장은 새 행을 복제하지 않고, 같은 과목의 뒤 차시 날짜를 뒤로 밀면서 `비고`에 연장일정을 기록합니다.
- 자동 배정은 과목별 수업시작일을 반영합니다.
- 숫자로 시작하지 않는 `대단원`은 자동 배정 대상에서 제외합니다.
- 국어 지도서 파싱은 `대단원 / 소단원 / 학습목표 / 실제 차시범위` 구조를 기준으로 생성합니다.

## 시트 구성

### 1. 진도표 시트

기본 시트명은 `시트1`이며 `.env`의 `SHEET_NAME`으로 바꿀 수 있습니다.

권장 열은 아래와 같습니다.

| 열 | 이름 | 필수 여부 | 설명 |
|---|---|---|---|
| A | 수업내용 | 권장 | 실제 수업 목표 또는 내용 |
| B | 과목 | 필수 | 예: 국어, 도덕 |
| C | 대단원 | 권장 | 자동 배정은 숫자로 시작하는 대단원만 대상으로 봄 |
| D | 차시 | 권장 | 예: `2(2~3)`, `6`, `11(11~12)` |
| E | 계획일 | 필수 | `YYYY-MM-DD` 권장 |
| F | 실행여부 | 필수 취급 | 헤더가 없어도 F열이면 실행여부로 읽음 |
| G | pdf파일 | 선택 | 자료 연결용 |
| H | 시작페이지 | 선택 | 자료 연결용 |
| I | 끝페이지 | 선택 | 자료 연결용 |
| J | 비고 | 차시 연장 시 사실상 필수 | `[연장일정:YYYY-MM-DD,...]` 저장 |
| K | 연장횟수 | 선택 | 차시 연장 누적 횟수 |
| L | 소단원 | 선택 | 특히 국어에서 유용 |

중요한 규칙:

- `실행여부` 헤더를 쓰지 않으려면 반드시 F열이 실행여부 열이어야 합니다.
- F열은 체크박스로 만드는 것이 가장 안정적입니다.
- `비고` 열은 차시 연장 기능을 위해 권장합니다.

### 2. 기초시간표 시트

기본 시트명은 `기초시간표`입니다.

예시:

| 교시 | 월 | 화 | 수 | 목 | 금 |
|---|---|---|---|---|---|
| 1 | 영어 | 과학 | 국어 | 국어 | 국어 |
| 2 | 수학 | 과학 | 체육 | 국어 | 사회 |

같은 날 같은 과목이 두 번 들어 있으면 자동 배정도 그날 두 번 배정합니다.

### 3. 휴업일 시트

기본 시트명은 `휴업일`입니다.  
첫 열 또는 `날짜` 열에 휴업일을 적으면 그 날짜는 자동 배정에서 제외됩니다.

### 4. 수업시작일 시트

기본 시트명은 `수업시작일`입니다.

예시:

| 과목 | 수업시작일 |
|---|---|
| 국어 | 2026-03-16 |
| 도덕 | 2026-03-02 |

이 시트가 없거나 특정 과목이 비어 있으면 프로그램이 물어봅니다.  
그때 그냥 엔터를 치면 학기 시작일을 사용합니다.

## 환경 변수

`.env` 예시:

```env
SHEET_ID="구글시트 ID"
SHEET_NAME="시트1"
TIMETABLE_SHEET="기초시간표"
HOLIDAY_SHEET="휴업일"
SUBJECT_START_SHEET="수업시작일"

# 둘 중 하나 사용
GOOGLE_CREDENTIALS_JSON='{
  "type": "service_account"
}'
GOOGLE_CREDENTIALS_PATH="credentials.json"
```

## 설치

```bash
pip install -r requirements.txt
```

웹 UI까지 쓸 경우:

```bash
npm install
```

## `schedule.py`

대화형 메뉴와 CLI 모드를 함께 제공합니다.

### 자주 쓰는 명령

```bash
python schedule.py
python schedule.py today
python schedule.py tomorrow
python schedule.py thisweek
python schedule.py nextweek
python schedule.py next
python schedule.py progress
python schedule.py done 국어 2026-03-26
python schedule.py push 국어 7 2026-03-26
```

### 주요 기능

- 오늘 수업 조회
- 내일 수업 조회
- 이번 주 남은 수업 조회
- 다음 주 수업 조회
- 과목별 다음 차시 조회
- 과목별 진도율 조회
- 완료 처리
- 차시 연장
- 일정 밀기

### 차시 연장 규칙

- 연장할 차시를 직접 고릅니다.
- 몇 차시를 연장할지도 직접 고릅니다.
- 새 행을 만들지 않습니다.
- 선택한 차시는 `비고`에 연장일정을 기록합니다.
- 같은 과목의 뒤 차시들은 날짜가 뒤로 밀립니다.

## `auto_planner.py`

기초시간표, 휴업일, 수업시작일을 이용해 계획일을 넣습니다.

### 실행 예시

```bash
python auto_planner.py
python auto_planner.py --mode initial --start-date 3.2
python auto_planner.py --mode fill-blanks --start-date 2026-03-02
```

### 배정 모드

- `initial`: 계획일을 처음부터 다시 넣습니다. 실행여부와 기존 계획일을 무시합니다.
- `fill-blanks`: 미완료이면서 계획일이 비어 있는 행만 채웁니다.

### 배정 규칙

- 학기 시작일 기본값은 현재 연도 `3.2`입니다.
- `3.2`, `3/2`, `3-2`처럼 연도 없이 입력할 수 있습니다.
- 과목별 수업시작일 이후부터만 배정합니다.
- 시간표에 같은 과목이 두 번 있으면 그날 두 차시 배정합니다.
- `대단원`이 숫자로 시작하지 않으면 자동 배정에서 제외합니다.

## `map_guides_to_sheet.py`

국어/도덕 지도서 PDF를 읽어 진도표 기본 행을 만듭니다.
외부 API(통신비용) 없이 **PyMuPDF(fitz)**의 폰트 크기 및 화면 내 좌표를 분석(Heuristics 알고리즘)하여, 가장 큰 글씨를 '대단원', 다음 큰 글씨를 '차시'로 자동 유추하는 강력한 **범용 로컬 파싱 엔진**이 탑재되어 있습니다.

### 실행 예시

```bash
python map_guides_to_sheet.py
python map_guides_to_sheet.py --upload
python map_guides_to_sheet.py --upload --cleanup
```

### 국어 파싱 규칙

- `대단원`은 큰 단원명으로 저장합니다.
- `소단원`은 별도 열이 있으면 같이 저장합니다.
- `수업내용`은 상세 차시 페이지 왼쪽 상단의 `학습목표`를 우선 사용합니다.
- `차시`는 그 학습목표에 대응하는 실제 범위로 생성합니다.

예:

- `대단원`: `1. 생생하게 표현해요`
- `소단원`: `감각적 표현의 재미를 느끼며 시 감상하기`
- `차시`: `2(2~3)`
- `수업내용`: `감각적 표현을 이해할 수 있다.`

### 주의

- `소단원` 열이 시트에 없으면 업로드 시 무시됩니다.
- `실행여부` 헤더가 없더라도 F열에는 체크박스용 `False` 값이 들어갑니다.

## `map_general_guides_to_sheet.py`

기타 교과용 범용 지도서 매핑 스크립트입니다.

### 실행 예시

```bash
python map_general_guides_to_sheet.py --list-presets
python map_general_guides_to_sheet.py --subject 사회
python map_general_guides_to_sheet.py --subject 과학 --upload
python map_general_guides_to_sheet.py --all-presets --upload --cleanup
```

### 현재 preset

- 수학
- 사회
- 과학
- 음악
- 미술
- 체육
- 영어
- 실과

### 동작 방식

- 같은 `.env`, 같은 구글시트를 사용합니다.
- 먼저 연간 지도 계획 PDF를 찾고, 있으면 그 구조를 우선 사용합니다.
- 연간 계획 PDF가 없으면 PDF 이름과 초기 몇 페이지를 기준으로 휴리스틱 생성으로 떨어집니다.
- 과목마다 품질 차이가 있으므로 미리보기 후 업로드하는 흐름을 권장합니다.

## 웹 UI (스마트 진도표 대시보드)

디자인 및 모듈화 아키텍처가 업그레이드된 최신 React(Vite) + TailwindCSS 대시보드입니다. 모놀리식 단일 파일을 버리고, 상태 관리 로직(`useScheduleData`)과 뷰(`DashboardView`, `LessonListView`, `ActionsView`)를 분리 설계했습니다.

```bash
# 터미널 1 (백엔드)
python server.py

# 터미널 2 (프론트엔드)
npm run dev
```

### 웹 UI 주요 기능
- **단원별 상세 진도 (Tree View)**: `server.py`가 시트의 평면적인 행 배열을 묶어서 컴파일해주어, 현재 어떤 대단원의 몇 %를 달성 중인지 시각적으로 한눈에 확인할 수 있습니다.
- **수업 카드 렌더링**: 오늘/내일/다음주 수업 및 직전 완료 차시와 다음 차시를 직관적인 아이콘 카드들로 보여줍니다.
- **일괄 연기 및 연장**: 버튼 터치만으로 일정 N일 미루기와 미수행 수업 연장을 쉽게 트리거할 수 있습니다.

## 테스트

```bash
python -m unittest discover -s tests -v
python -m py_compile schedule.py auto_planner.py map_guides_to_sheet.py
```

현재 테스트는 다음 범위를 다룹니다.

- 일정 조회/완료/밀기/연장
- F열 실행여부 fallback
- `'true`, `'false` 보정
- 자동 배정 모드와 시작일 규칙
- 국어 지도서 파싱

## 운영 메모

- Google Sheets가 진짜 운영 데이터입니다.
- 엑셀 파일은 구조 확인용 참고 자료로만 사용합니다.
- 체크박스 열은 헤더 없이 F열로 두는 방식도 지원합니다.
- 쿼터 문제를 피하기 위해 시트 읽기는 가능한 한 한 번에 처리하도록 구현되어 있습니다.
