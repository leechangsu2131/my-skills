---
name: teacherlesson-from-neis
description: "NEIS 주간학습안내에서 날짜·교시별 수업내용을 읽어 오늘/주간/월간 수업 뷰어에 표시하는 읽기 전용 스킬."
metadata:
  category: 수업·교사 도구
  status: 운영
  version: Chrome 확장 v1.1.0
  summary: NEIS 주간학습안내를 읽어 등록된 주차를 자동 동기화하고, 오늘 수업 플로팅 패널과 로컬 주간·월간 뷰어에 표시한다. 조회 전용이며 자료는 이 PC의 Chrome 저장소와 로컬 뷰어에서 관리한다.
---

# Teacher Lesson From NEIS

NEIS의 주간학습안내 데이터를 현재 로그인된 Chrome 세션에서 읽어 NEIS 화면의 왼쪽 아래 플로팅 패널과 확장 프로그램 안의 수업 뷰어에 표시합니다. 뷰어는 Chrome `storage.local`을 직접 읽으므로 별도 Python 서버를 켤 필요가 없습니다. `teacherlesson-schedule`의 날짜·교시 중심 보드 구성을 참고하지만 Google Sheets 진도표나 수업배치 시트에는 접근하지 않습니다.

`server.py`, `web/`, `실행_나이스수업뷰어.bat`은 이전 확장 버전과의 호환용이며 현재 버전의 일상 사용에는 필요하지 않습니다.

전체 뷰어는 하루 상세, 월~금 주간 보드, 날짜별 요약이 있는 월간 달력을 제공합니다. 월간 보기에서는 날짜 칸 높이를 조절하고 `+N개 수업`을 눌러 그날의 전체 수업을 펼치거나 토·일 표시를 전환할 수 있습니다. 월간 날짜를 누르면 하루 상세 보기로 이동하며, 날짜 선택과 이전/다음 이동은 세 보기의 기준 날짜를 함께 바꿉니다.

## 사용자 흐름

1. Chrome 확장 프로그램을 설치/활성화합니다.
2. Chrome에서 NEIS에 로그인하고 `교육과정 > 주간학습안내작성` 화면을 엽니다.
3. 주간학습안내에서 한 번 정상 조회하면 현재 주와 `dsWeekList`에 있는 나머지 주차까지 자동으로 읽어옵니다. 이후 조회에서는 현재 주를 갱신하고 12시간 지난 주만 다시 가져옵니다.
4. NEIS 화면 왼쪽 아래 플로팅 패널이나 확장 프로그램 메뉴의 **오늘의 수업 뷰어 열기**에서 오늘/주간/월간 수업을 확인합니다.

월간 가져오기는 확장 팝업에서 달을 선택해 실행할 수 있습니다. `dsWeekList`에서 해당 월과 겹치는 주차를 골라 순차 조회한 뒤 원래 주차를 다시 표시합니다. `dsWikLrn`에 미저장 수업내용 변경이 있으면 자동/수동 동기화를 중단합니다. 다른 화면 데이터셋의 변경 상태는 수업내용 조회를 막지 않습니다. 자세한 갱신·캐시 흐름은 [docs/auto-sync.md](docs/auto-sync.md)를 참고합니다.

## 파일 지도

- `extension/viewer.html`, `extension/viewer.js`, `extension/viewer.css`: Chrome 저장자료를 직접 읽는 하루/주간/월간 뷰어
- `extension/manifest.json`: Chrome MV3 권한과 팝업 정의
- `extension/neis-reader.js`: NEIS 조회 감지, 등록 주차별 자동 조회, 수업 데이터 정규화
- `extension/content.js`: NEIS 페이지의 플로팅 오늘 수업 패널
- `extension/background.js`: 12시간 주별 캐시와 Chrome 로컬 저장소 관리, 플로팅 패널에서 뷰어 열기
- `extension/popup.js`: 월간 가져오기, 수동 재동기화, 전체 뷰어 열기
- `docs/data-contract.md`: NEIS 필드와 정규 레코드 매핑
- `docs/auto-sync.md`: 자동 주차 동기화와 캐시 동작, 제한사항

## 안전과 데이터 보관

- 조회 화면의 `dsWikLrn`만 읽습니다. 저장·수정·결재 제출은 호출하지 않습니다.
- NEIS 자격 증명, 쿠키, 인증 토큰, 원본 네트워크 본문을 읽거나 별도 저장하지 않습니다.
- NEIS 주간 조회가 끝나면 현재 주와 캐시가 없거나 만료된 `dsWeekList` 주차를 자동 동기화합니다. 월간 가져오기는 팝업에서 사용자가 실행합니다.
- 정규 수업자료는 Chrome 확장 저장소에 이 PC 전용으로 보관합니다. 플로팅 패널과 전체 뷰어가 같은 저장자료를 직접 읽어 서버 실행 여부에 영향을 받지 않습니다.
- 주간학습 데이터셋 `dsWikLrn`에 수정 표시가 있으면 동기화를 중단합니다. 다른 데이터셋의 수정 표시는 수업내용 동기화를 막지 않습니다.

## 변경 시 확인할 곳

- NEIS 필드/화면 변경: `docs/data-contract.md`, `extension/neis-reader.js`, `extension/popup.js`
- 화면 표시와 저장자료 조회: `extension/viewer.*`
- 사용 안내: `README.md`
