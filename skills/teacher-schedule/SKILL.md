---
name: teacher-schedule
description: "구글 시트 기반 교사 수업 관리 스킬. schedule.py, bridge_sheet.py, auto_planner.py, server.py, src/를 중심으로 작업하며, 현재 구조는 진도표와 수업배치를 분리해 운영한다."
---

# Teacher Schedule Skill

이 스킬은 교사의 수업 진도와 수업배치를 함께 관리하는 저장소를 다룹니다.

## 범위

포함:

- `schedule.py`
- `bridge_sheet.py`
- `auto_planner.py`
- `server.py`
- `src/`
- `tests/test_schedule.py`
- `tests/test_auto_planner.py`
- `tests/test_bridge_sheet.py`

제외:

- 지도서 PDF 분할
- 지도서 내용을 시트 행으로 매핑/업로드

관련 별도 저장소:

- `C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\teacher-guide-sheet-mapper`

## 현재 구조

핵심 개념:

- `진도표`: 무엇을 가르칠지 관리
- `수업배치`: 언제 / 몇 교시에 가르칠지 관리
- `lesson_id`: 진도표와 수업배치를 연결하는 키

현재는 날짜/교시의 진실 원천을 `수업배치`로 둡니다.

- `schedule.py` 조회/완료/밀기/연장은 브릿지 시트가 있으면 `수업배치` 기준으로 동작
- `server.py`와 `src/`도 같은 기준으로 조회
- `진도표.계획일`, `진도표.계획교시`는 브릿지에서 역동기화되는 표시 컬럼

## 우선순위

1. `schedule.py`
2. `bridge_sheet.py`
3. `auto_planner.py`
4. `server.py`
5. `src/`
6. 테스트

## 작업 원칙

- 실제 운영 데이터는 Google Sheets다.
- `lesson_id`를 `_row`보다 우선한다.
- 브릿지 시트가 있으면 날짜/교시는 `수업배치`를 기준으로 본다.
- 완료 처리는 가능한 한 슬롯 단위로 처리한다.
- 같은 `lesson_id`가 여러 슬롯에 걸쳐 있으면 마지막 planned 슬롯이 사라질 때만 `진도표.실행여부`를 완료로 본다.
- 진도표의 본문 컬럼과 수업배치의 슬롯 컬럼을 섞어 쓰지 않는다.
- `계획일`을 직접 수정하는 것보다 브릿지 갱신 경로를 우선한다.

## 주의할 점

- 실제 `진도표` 헤더가 브릿지 헤더로 덮여도 복구해서 읽도록 되어 있다.
- `실행여부` 헤더가 없으면 F열 fallback이 여전히 적용된다.
- 숫자로 시작하지 않는 `대단원`은 자동 배치 대상에서 빠질 수 있다.
- CLI와 UI 둘 다 브릿지 기준으로 맞춰야 한다. 한쪽만 바꾸면 표시와 실제 동작이 어긋난다.
- 문서 수정 시에는 `진도표 / 수업배치` 역할 분리를 기준으로 설명을 맞춘다.

## 바꿀 때 같이 볼 파일

### `schedule.py`를 바꿀 때

- `tests/test_schedule.py`
- 필요하면 `server.py`
- 필요하면 `src/hooks/useScheduleData.js`

### `bridge_sheet.py`를 바꿀 때

- `tests/test_bridge_sheet.py`
- `schedule.py`
- `docs/bridge-sheet-design.md`

### `auto_planner.py`를 바꿀 때

- `tests/test_auto_planner.py`
- `bridge_sheet.py`

### UI를 바꿀 때

- `server.py`
- `src/hooks/useScheduleData.js`
- `src/components/`

## 자주 쓰는 명령

```bash
python schedule.py
python schedule.py today
python schedule.py nextweek
python schedule.py next
python schedule.py progress

python bridge_sheet.py

python auto_planner.py --mode initial --start-date 3.2
python auto_planner.py --mode fill-blanks --start-date 2026-03-02

python -m unittest tests.test_schedule tests.test_auto_planner tests.test_bridge_sheet
python -m py_compile schedule.py auto_planner.py bridge_sheet.py server.py
npm run build
```

## 문서 기준

아키텍처 설명은 아래 문서를 기준으로 맞춘다.

- [bridge-sheet-design.md](C:/Users/user/.gemini/antigravity/scratch/repos/my-skills/skills/teacher-schedule/docs/bridge-sheet-design.md)
