# 다기업 분석 + 결과 자동 저장 태스크 트래커

| 작업 (Task) | 상태 (Status) | 비고 (Notes) |
| :--- | :---: | :--- |
| export_builder.py 신규 생성 | 완료 (x) | 완료 |
| export_saver.py 신규 생성 | 완료 (x) | 완료 |
| dashboard.py 관련 작업 | 완료 (x) | 완료 |
| 🔬 K열 '섹터 PER' 변경 및 industry_context.json 리서치 자동화 | 완료 (x) | 완료 |
| **[신규] 지표 개념 지도 및 데이터 정리 작업** | | |
| 1. 잘못된 데이터 클린업 (이전 파이낸스차트 잔재 및 시트 데이터 정리) | 완료 (x) | 정리 완료 |
| 2. `metric_config.json` 개념 지도 메타데이터 정의 (Fallback 전략) | 진행 중 (/) | 표준화 설정 파일 구성 |
| 3. `layer1_store.py` 헤더 확장 (op_margin 등) | 완료 (x) | 스키마 확장 완료 |
| 4. `us_pipeline.py` (Yahoo) 영업마진 추가 | 완료 (x) | `operatingMargins` 추출 반영 완료 |
| 5. `ingest_financecharts.py` 비활성화 | 완료 (x) | Cloudflare 차단으로 인한 스크래퍼 제외 |
| 6. `ingest_gurufocus.py` ROIC 및 영업마진 추가 | 완료 (x) | `ROIC %`, `Operating Margin %` 추출 반영 완료 |
| 7. NVDA 티커 파이프라인 전체 재실행 및 시트 검증 | 완료 (x) | 동작 테스트 및 데이터 검증 완료 |
