---
name: teacherlesson-from-neis
description: "NEIS 주간학습안내에서 날짜·교시별 수업내용을 읽어 오늘/주간/월간 수업 뷰어에 표시하는 읽기 전용 스킬."
---

# Teacher Lesson From NEIS

NEIS의 주간학습안내 데이터를 현재 로그인된 Chrome 세션에서 읽어 NEIS 화면의 왼쪽 아래 플로팅 패널과 로컬 수업 뷰어에 표시합니다. `teacherlesson-schedule`의 날짜·교시 중심 보드 구성을 참고하지만 Google Sheets 진도표나 수업배치 시트에는 접근하지 않습니다.

## 사용자 흐름

1. 로컬 뷰어를 `실행_나이스수업뷰어.bat`으로 시작합니다.
2. Chrome에서 NEIS에 로그인하고 `교육과정 > 주간학습안내작성` 화면을 엽니다.
3. 주간학습안내에서 한 번 정상 조회하면 현재 주와 `dsWeekList`에 있는 나머지 주차까지 자동으로 읽어옵니다. 이후 조회에서는 현재 주를 갱신하고 12시간 지난 주만 다시 가져옵니다.
4. NEIS 화면 왼쪽 아래 플로팅 패널 또는 로컬 뷰어에서 오늘 수업을 확인합니다.

월간 가져오기는 확장 팝업에서 달을 선택해 실행할 수 있습니다. `dsWeekList`에서 해당 월과 겹치는 주차를 골라 순차 조회한 뒤 원래 주차를 다시 표시합니다. `dsWikLrn`에 미저장 수업내용 변경이 있으면 자동/수동 동기화를 중단합니다. 다른 화면 데이터셋의 변경 상태는 수업내용 조회를 막지 않습니다. 자세한 갱신·캐시 흐름은 [docs/auto-sync.md](docs/auto-sync.md)를 참고합니다.

## 파일 지도

- `server.py`: loopback 전용 Flask API와 정적 뷰어 서버
- `web/index.html`, `web/app.js`, `web/style.css`: 오늘/주간/월간 수업 뷰어
- `extension/manifest.json`: Chrome MV3 권한과 팝업 정의
- `extension/neis-reader.js`: NEIS 조회 감지, 등록 주차별 자동 조회, 수업 데이터 정규화
- `extension/content.js`: NEIS 페이지의 플로팅 오늘 수업 패널
- `extension/background.js`: 12시간 주별 캐시, 로컬 확장 저장소 보관과 뷰어 API 동기화
- `extension/popup.js`: 월간 가져오기와 수동 재동기화
- `실행_나이스수업뷰어.bat`: `127.0.0.1:5101`에서 로컬 서버 시작
- `docs/data-contract.md`: NEIS 필드와 정규 레코드 매핑
- `docs/auto-sync.md`: 자동 주차 동기화와 캐시 동작, 제한사항

## 안전과 데이터 보관

- 조회 화면의 `dsWikLrn`만 읽습니다. 저장·수정·결재 제출은 호출하지 않습니다.
- NEIS 자격 증명, 쿠키, 인증 토큰, 원본 네트워크 본문을 읽거나 별도 저장하지 않습니다.
- NEIS 주간 조회가 끝나면 현재 주와 캐시가 없거나 만료된 `dsWeekList` 주차를 자동 동기화합니다. 월간 가져오기는 팝업에서 사용자가 실행합니다.
- 정규 수업자료는 Chrome 확장 저장소에 이 PC 전용으로 보관합니다. 로컬 뷰어 서버에는 현재 메모리로 전달하며, 서버 재시작 후에도 플로팅 패널은 저장 자료를 표시합니다.
- 주간학습 데이터셋 `dsWikLrn`에 수정 표시가 있으면 동기화를 중단합니다. 다른 데이터셋의 수정 표시는 수업내용 동기화를 막지 않습니다.

## 변경 시 확인할 곳

- NEIS 필드/화면 변경: `docs/data-contract.md`, `extension/neis-reader.js`, `extension/popup.js`
- API 검증/보관 정책: `server.py`
- 화면 표시: `web/`
- 사용 안내: `README.md`
