# 다기업 분석 + 결과 자동 저장 태스크 트래커

| 작업 (Task) | 상태 (Status) | 비고 (Notes) |
| :--- | :---: | :--- |
| export_builder.py 신규 생성 (마크다운/JSON 빌드 로직 추출) | 완료 (x) | 완료 (순수 함수) |
| export_saver.py 신규 생성 (일자별 덮어쓰기 저장) | 완료 (x) | 완료 (results/{ticker}_{company}/{YYYY-MM-DD}) |
| dashboard.py 종목 선택기 (사이드바 셀렉트박스) | 완료 (x) | 완료 |
| dashboard.py 하드코딩 제거 (제목, 경로 동적화) | 완료 (x) | 완료 |
| dashboard.py 실시간 자동 저장 로직 및 이력 표시 | 완료 (x) | 완료 (수동 버튼 제거) |
| dashboard.py 기존 Export 로직을 export_builder 호출로 교체 | 완료 (x) | 완료 |
| 컴파일 및 기존 테스트 통과 확인 | 완료 (x) | 104개 테스트 모두 통과 |
