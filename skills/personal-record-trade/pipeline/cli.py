import sys
import argparse

# Windows cp949 인코딩 오류 방지
if hasattr(sys.stdout, 'reconfigure'):
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8')

from pipeline.dart_fetcher import get_dart_data
from pipeline.market_fetcher import get_market_data
from pipeline.llm_mapper import map_dart_to_metrics
from pipeline.generator import save_valuation_data

def run_pipeline(ticker: str, year: int, quarter: str = "A"):
    print("========================================")
    print(f"🚀 가치평가 데이터 파이프라인 가동 (종목: {ticker}, 연도: {year}, 분기: {quarter})")
    print("========================================")

    # 1. Market Data 수집
    print("\n[단계 1/4] 시장 데이터(시가총액, 주가) 수집...")
    market_data = get_market_data(ticker)
    if not market_data:
        print("[실패] 시장 데이터를 수집하지 못했습니다. 파이프라인을 중단합니다.")
        sys.exit(1)

    # 2. DART Data 수집
    print(f"\n[단계 2/4] DART 재무제표(Raw) 수집 ({year}년 {quarter})...")
    dart_records = get_dart_data(ticker, year, quarter)
    if not dart_records:
        print("[실패] DART 데이터를 수집하지 못했습니다. 종목코드나 연도를 확인하세요.")
        sys.exit(1)

    # 2.5 yfinance Data 병렬 수집
    print(f"\n[단계 2.5/4] yfinance 데이터 병렬 수집 ({year}년 {quarter})...")
    from pipeline.yfinance_fetcher import get_yfinance_metrics
    yf_data = get_yfinance_metrics(ticker, year, quarter)
    if not yf_data:
        print("[경고] yfinance 데이터 수집 실패, DART 데이터만으로 진행합니다.")

    # 3. Parsing & Mapping
    print("\n[단계 3/4] 표준 규격(metrics.json) 매핑...")
    metrics_data = map_dart_to_metrics(dart_records, year, quarter, yf_data=yf_data)
    if not metrics_data:
        print("[실패] 매핑에 실패했습니다.")
        sys.exit(1)

    # 4. Save to Database (JSON)
    print("\n[단계 4/4] 로컬 파일 시스템에 저장...")
    save_valuation_data(ticker, market_data, metrics_data)

    print("\n🎉 모든 파이프라인 작업이 완료되었습니다! 대시보드(dashboard.py)를 실행해보세요.")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Valuation Data Pipeline CLI")
    parser.add_argument("ticker", type=str, help="종목코드 (예: 009150)")
    parser.add_argument("year", type=int, help="수집할 사업연도 (예: 2024)")
    parser.add_argument("--quarter", type=str, default="A", help="분기 (A, Q1, H1, Q3)")
    
    args = parser.parse_args()
    run_pipeline(args.ticker, args.year, args.quarter)
