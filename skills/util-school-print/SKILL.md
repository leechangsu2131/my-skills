---
name: util-school-print
description: "한글(HWP) OLE 자동화로 학년/반별 안내장을 배치 인쇄하고, 반 구분 간지를 자동 삽입하는 Windows 전용 스킬입니다."
---

# 학교 안내장 반별 자동 인쇄 스킬

한글(HWP) OLE COM 자동화와 `win32` 기반 인쇄를 사용해, 반마다 별도 인쇄 Job을 전송합니다.  
핵심은 **반별 Job 경계 유지 + 간지 자동 삽입**입니다.

## 포함 파일

| 파일 | 설명 |
|---|---|
| `batch_print_v2.py` | 반별 안내장 인쇄 + 간지 자동 삽입 스크립트 |
| `.env` | 경로·인쇄 설정 (여기만 수정하면 됨) |
| `run_print.bat` | 더블클릭 실행용 배치 파일 |
| `간지_템플릿_안내.html` | 간지 템플릿(HWPX) 작성 안내 |

## 준비물 (hwpprint 폴더)

`C:\Users\user\Documents\hwpprint` 안에 아래 파일 준비:

```
hwpprint/
├── *안내장.hwpx          ← 인쇄할 안내장 (실행 시 목록에서 선택)
├── 학생명렬표.xlsx        ← 학년/반/학생수 컬럼 포함
└── 간지_템플릿.hwpx       ← {{학년}} {{반}} {{학생수}} 플레이스홀더 포함
```

## 동작 구조

```text
실행 → *안내장.hwpx 목록 표시 → 번호 선택
         ↓
엑셀 or 구글시트에서 반 데이터 로드
         ↓
[간지] 1학년 1반 · 21명  1장 인쇄
 안내장 21장 인쇄
[간지] 1학년 2반 · 20명  1장 인쇄
 안내장 20장 인쇄
 ...
```

## 설치

```powershell
pip install pywin32 openpyxl python-dotenv
```

## 설정 (.env)

```env
# ── 파일 경로 ──────────────────────────────────────────
HWPX_DIR=C:\Users\user\Documents\hwpprint
EXCEL_FILE=C:\Users\user\Documents\hwpprint\학생명렬표.xlsx
SEPARATOR_TEMPLATE=C:\Users\user\Documents\hwpprint\간지_템플릿.hwpx

# ── Google Sheets (비워두면 EXCEL_FILE 사용) ───────────
GOOGLE_SHEET_CSV_URL=https://docs.google.com/spreadsheets/d/<ID>/export?format=csv&gid=<GID>

# ── 인쇄 설정 ──────────────────────────────────────────
PRINTER_NAME=FUJIFILM Apeos C2561 3연구실   # 비워두면 기본 프린터
JOB_DELAY=3
DRY_RUN=false        # true → 실제 인쇄 없이 목록만 출력
DUPLEX=1             # 0=단면 / 1=양면(긴면/책형) / 2=양면(짧은면/달력형)

# ── 트레이 제어 (간지와 안내장 분리) ──────────────────
# 간지는 색지가 들어있는 별도 트레이(예: 트레이2)에서, 안내장은 기본 트레이(예: 트레이1)에서 나옵니다.
# 프린터 모델마다 트레이 식별 번호가 다르므로 `list_trays.bat`을 실행해 확인한 번호를 입력하세요.
SEPARATOR_TRAY=3     # 간지를 빼낼 트레이 번호 (예: 후지필름 기준 트레이2의 내부 번호=3)
```

> **단면/양면 분리**: 간지는 항상 단면(`duplex=0`)으로 코드가 강제 고정합니다.
> **트레이 제어의 원리**: HWP OLE는 용지함 강제 제어를 사실상 무시합니다. 스크립트는 `win32print`를 사용해 인쇄 순간 시스템의 **프린터 사용자 기본 설정(PRINTER_INFO_9의 dmDefaultSource)**을 임시로 빠르게 변경하는 방식으로 우회하여 관리자 권한 충돌 없이 트레이를 제어합니다.

## 트레이 번호 찾기 (list_trays)

프린터 제조사마다 1번 트레이가 `1`이 아닐 수 있습니다. 올바른 트레이 번호를 찾으려면:
```powershell
list_trays.bat
```
를 더블클릭하여 표시된 목록에서 "트레이 2" 또는 "수동" 등 원하는 용지함의 실제 숫자 번호(예: `262`, `3` 등)를 찾아 `.env`에 입력합니다.

## 실행 방법

```
run_print.bat 더블클릭
```

또는 터미널에서:

```powershell
python batch_print_v2.py
```

실행 시 `*안내장.hwpx` 파일 목록이 표시되고 번호를 선택하면 인쇄가 시작됩니다.

## 구글시트 연동 (API 없이)

1. 시트 공유를 "링크가 있는 사용자(뷰어)"로 설정
2. CSV export URL 형태:  
   `https://docs.google.com/spreadsheets/d/<ID>/export?format=csv&gid=<GID>`
3. `.env`의 `GOOGLE_SHEET_CSV_URL`에 입력

시트 연동 실패 시 자동으로 로컬 엑셀 파일로 대체합니다.

## 프린터 이름 확인

```powershell
Get-Printer | Select-Object Name, Default | Format-Table -AutoSize
```

## 주의사항

- **용지 여백 확보 필수 (Auto Tray Switching 주의)**: 프린터의 1번 트레이(안내장 본문용)에 A4 용지가 다 떨어질 경우 기기가 알아서 2번 트레이(간지용 색지) 등 다른 용지함의 A4 용지를 끌어다 쓰는 불상사(색지에 엄청난 안내장이 잘못 출력되는 참사)가 발생할 수 있습니다. **반드시 전체 인쇄 매수보다 넉넉하게 본문용 A4 용지를 채워둔 후 실행**하세요.
- Windows 전용 (HWP OLE 특성상)
- 한글 2018 이상 권장
- 인쇄 누락 시 `JOB_DELAY`를 5초 이상으로 증가
- 점검 시 `DRY_RUN=true`로 실제 인쇄 없이 순서·매수 확인
- 엑셀 컬럼명 기본값: `학년` / `반` / `학생수`

## 디버깅 및 트러블슈팅 기록

프린터의 용지함(트레이) 제어 오류(액세스 거부) 해결 과정과 OLE 자동화 권한 문제 회피(Level 9)에 대한 개발 비하인드 스토리는 [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)에 상세히 기록되어 있습니다. 향후 환경이 바뀌거나 프린터가 변경되어 비슷한 문제가 발생하면 참고하시기 바랍니다.
