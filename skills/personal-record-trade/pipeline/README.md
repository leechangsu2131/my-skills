# Pipeline

이 폴더(`pipeline/`)는 종목의 기본적 분석(Fundamental Analysis)과 시장 데이터(Market Data)를 수집하고 가공하여 `raw data` 시트나 로컬 저장소로 파이프라이닝하는 **데이터 수집 및 매핑 엔진**입니다.

## 주요 기능 (Core Capabilities)
- **미국 주식 및 글로벌 데이터 파싱:** `yfinance_fetcher.py`, `ingest_gurufocus.py`, `ingest_financecharts.py` 등을 활용해 EPS, PER, PBR, FCF 등 핵심 재무 지표를 긁어옵니다. (`us_pipeline.py`로 통합)
- **한국 주식 데이터 수집:** `dart_fetcher.py`를 통해 금융감독원 DART 시스템에서 공시 데이터를 수집합니다.
- **애널리스트 리포트 인제스천:** `ingest_report.py`, `estimate_aggregator.py` 등을 통해 증권사 리포트의 텍스트와 실적 추정치 테이블을 분석 및 가공합니다.
- **LLM 매핑 및 정규화:** `llm_mapper.py`, `unified_metrics.py`를 활용해 파편화된 데이터 소스의 지표들을 시스템 표준 열(Column)에 맞게 정규화합니다.
- **산업 리서치 컨텍스트:** `research_industry_context.py`를 통해 종목이 속한 산업군의 매크로 데이터 및 피어 그룹(Peer Group) 컨텍스트를 분석합니다.

## 활용 방법 (Usage)
- 새로운 종목 데이터를 긁어오거나, 구글 시트의 `raw data`를 업데이트할 때 이 폴더 내의 스크립트들을 활용합니다. (예: `python us_pipeline.py --ticker NVDA`)
