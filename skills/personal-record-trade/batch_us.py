"""
미국 개별주 배치 파이프라인 실행 스크립트
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from pipeline.us_pipeline import run_us_pipeline

US_STOCKS = [
    "GOOG",   # Alphabet
    "NVDA",   # NVIDIA
    "META",   # Meta
    "PLTR",   # Palantir
    "NFLX",   # Netflix
    "ADBE",   # Adobe
    "UNH",    # UnitedHealth
    "ORCL",   # Oracle
    "RDDT",   # Reddit
    "APP",    # AppLovin
    "HOOD",   # Robinhood
    "NOW",    # ServiceNow
    "CRM",    # Salesforce
    "WDAY",   # Workday
    "NTNX",   # Nutanix
]

PERIODS = [
    (2024, "A"),
    (2025, "A"),
]

def main():
    total = len(US_STOCKS) * len(PERIODS)
    done = 0
    success = 0
    skipped = 0
    
    for ticker in US_STOCKS:
        for year, quarter in PERIODS:
            done += 1
            print(f"\n{'#'*60}")
            print(f"# [{done}/{total}] {ticker} — {year} {quarter}")
            print(f"{'#'*60}")
            try:
                result = run_us_pipeline(ticker, year, quarter)
                if result:
                    success += 1
                else:
                    skipped += 1
            except Exception as e:
                print(f"[오류] {ticker} {year}{quarter}: {e}")
                skipped += 1
    
    print(f"\n{'='*60}")
    print(f"✅ 미국 개별주 배치 완료!")
    print(f"   성공: {success}건 / 건너뜀: {skipped}건 / 총 {total}건")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
