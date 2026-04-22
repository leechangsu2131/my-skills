---
name: util-school-print
description: "한글(HWP) OLE 자동화로 학년/반별 안내장을 배치 인쇄하고, 반 구분 간지를 자동 삽입하는 Windows 전용 스킬입니다."
---

# 학교 안내장 반별 자동 인쇄 스킬

한글(HWP) OLE COM 자동화와 `win32` 기반 인쇄를 사용해, 반마다 별도 인쇄 Job을 전송합니다.  
핵심은 **반별 Job 경계 유지 + 간지 자동 삽입**입니다.

## 포함 파일

- `batch_print_v2.py`: 반별 안내장 인쇄 + 간지 자동 삽입 스크립트
- `간지_템플릿_안내.html`: 간지 템플릿(HWPX) 작성 안내

## 동작 구조

```text
엑셀(학생 명렬표) 읽기
        ↓
[간지] 3학년 1반 · 17명 1장 인쇄
안내장 17장 인쇄
[간지] 3학년 2반 · 18명 1장 인쇄
안내장 18장 인쇄
...
```

프린터에서 Job 단위로 출력되므로 반별 묶음을 나누기 쉽습니다.

## 설치

```powershell
pip install pywin32 openpyxl
```

## 사용 방법

1. `batch_print_v2.py` 상단 경로를 실제 환경에 맞게 수정
   - `HWPX_FILE`
   - `EXCEL_FILE`
   - `SEPARATOR_TEMPLATE`
   - (선택) `GOOGLE_SHEET_CSV_URL`
2. 필요 시 `PRINTER_NAME`, `JOB_DELAY`, `DRY_RUN` 조정
3. 실행:

```powershell
python batch_print_v2.py
```

## 구글시트 연동 (API 없이)

- 권장: 연동용 시트에 `학년`, `반`, `학생수` 3컬럼으로 관리
- 공유를 "링크가 있는 사용자(뷰어)"로 열고 CSV export URL 사용:

```text
https://docs.google.com/spreadsheets/d/<SHEET_ID>/export?format=csv&gid=<GID>
```

- 해당 URL을 `GOOGLE_SHEET_CSV_URL`에 넣으면 스크립트가 먼저 시트에서 읽고, 실패 시 로컬 엑셀로 자동 대체합니다.

## 프린터 설정(권장)

- Windows 프린터 속성에서 **교대 배출(Job Offset)** 활성화
- 가능하면 간지는 색지 트레이(예: 트레이2)로 지정

## 메일머지 vs 간지 삽입

- **메일머지 필요**: 학생별로 이름/번호 등 개인화 내용이 다른 경우
- **메일머지 불필요**: 동일 안내장을 반별 매수만 다르게 출력하는 경우

이 스킬의 기본 시나리오는 후자이며, 이때는 메일머지보다 간지 자동 삽입이 단순하고 안정적입니다.

## 주의사항

- Windows 전용 (HWP OLE 특성상)
- 한글 2018 이상 권장
- 인쇄 누락 시 `JOB_DELAY`를 3초 → 5초 이상으로 증가
- 점검 시 `DRY_RUN = True`로 실제 인쇄 없이 순서/매수 확인
- 엑셀 컬럼명은 기본값 기준 `학년` / `반` / `학생수`
