"""
batch_portfolio_valuation.py
───────────────────────────
구글 스프레드시트의 '📊 포트폴리오' 탭에서 종목코드를 읽어와
한국/미국 주식에 맞는 가치평가 파이프라인을 일괄 실행합니다. (5개년 수집 및 단일 통합 JSON 생성 추가)
"""

import os
import sys
import re
import json
from pathlib import Path
from datetime import datetime

# Enforce UTF-8 for stdout and stderr to prevent CP949 encoding errors on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

# .env 로드를 가장 먼저 수행하여 KRX_ID 등 환경변수가 설정되도록 함
from dotenv import load_dotenv
load_dotenv()

from gsheet_auth import get_client
from pipeline.cli import run_pipeline
from pipeline.us_pipeline import run_us_pipeline

# 사용자 지정 스프레드시트 정보
SHEET_ID = "12csrOj-6xgW45JSjbh8O9okxmA34eaatszvio6hQlmc"
PORTFOLIO_GID = 1127641143

# 구글 시트 403 API 에러 대비 로컬 백업 데이터
FALLBACK_PORTFOLIO = [
    ["S","Alphabet(GOOGL)","달러","GOOG"],
    ["S","NVIDIA Corp","달러","NVDA"],
    ["S","UnitedHealth(UNH)","달러","UNH"],
    ["S","아이스크림미디어","원","461300"],
    ["S","RISE 200 TR","원","361580"],
    ["S","Meta Platforms","달러","META"],
    ["A-","비트코인","BTC","BTC"],
    ["A-","Palantir(PLTR)","달러","PLTR"],
    ["A","현대해상","원","001450"],
    ["A","Netflix(NFLX)","달러","NFLX"],
    ["A-","Adobe(ADBE)","달러","ADBE"],
    ["A-","NAVER","원","035420"],
    ["A+","현대일렉트릭","원","267260"],
    ["A","Reddit(RDDT)","달러","RDDT"],
    ["A-","SK하이닉스","원","000660"],
    ["B+","Oracle(ORCL)","달러","ORCL"],
    ["B+","Robinhood(HOOD)","달러","HOOD"],
    ["A","Applovin(APP)","달러","APP"],
    ["A","삼성전기","원","009150"]
]


def load_portfolio_from_sheet():
    """구글 시트에서 포트폴리오 목록을 읽어옵니다. 권한 문제 발생 시 로컬 백업을 사용합니다."""
    print("[INFO] Loading portfolio data from Google Sheet...")
    try:
        client = get_client()
        doc = client.open_by_key(SHEET_ID)
        
        target_ws = None
        for ws in doc.worksheets():
            if ws.id == PORTFOLIO_GID:
                target_ws = ws
                break
                
        if not target_ws:
            target_ws = doc.get_worksheet(0)
            
        print(f"[OK] Worksheet '{target_ws.title}' loaded.")
        records = target_ws.get_all_records()
        
        portfolio = []
        for row in records:
            code = str(row.get("코드", "")).strip()
            currency = str(row.get("통화", "")).strip()
            name = str(row.get("종목명", "")).strip()
            if code and currency:
                portfolio.append([row.get("등급", ""), name, currency, code])
                
        print(f"[OK] Retrieved {len(portfolio)} rows from sheet.")
        return portfolio
        
    except Exception as e:
        print(f"[WARN] Failed to load from Google Sheet ({type(e).__name__}). Using local fallback portfolio.")
        return [["S", item[1], item[2], item[3]] for item in FALLBACK_PORTFOLIO]


def clean_ticker(ticker_str: str) -> str:
    """티커나 종목코드의 불필요한 공백이나 문자를 제거합니다."""
    return re.sub(r'[^a-zA-Z0-9]', '', ticker_str)


def is_valid_kr_ticker(ticker_str: str) -> bool:
    """6자리 숫자로 구성된 한국 주식 코드인지 판별합니다."""
    return bool(re.match(r'^\d{6}$', ticker_str))


def is_valid_us_ticker(ticker_str: str) -> bool:
    """알파벳으로 구성된 미국 주식 티커인지 판별합니다."""
    return bool(re.match(r'^[a-zA-Z]{1,5}$', ticker_str))


def create_combined_json():
    """개별 저장된 데이터를 하나로 결합하여 combined_portfolio_valuation.json을 생성합니다."""
    print(f"\n{'-'*30} CREATING COMBINED PORTFOLIO VALUATION JSON {'-'*30}")
    valuation_dir = Path(__file__).parent.resolve() / "data" / "valuation"
    
    combined_data = {
        "generated_at": datetime.now().isoformat(),
        "companies": {}
    }
    
    if not valuation_dir.exists():
        print(f"[ERROR] Valuation directory {valuation_dir} does not exist.")
        return
        
    for p in valuation_dir.iterdir():
        if p.is_dir() and (is_valid_kr_ticker(p.name) or is_valid_us_ticker(p.name)):
            ticker = p.name
            market_path = p / "normalized" / "market.json"
            metrics_path = p / "normalized" / "metrics.json"
            
            if market_path.exists() and metrics_path.exists():
                try:
                    with market_path.open("r", encoding="utf-8") as f:
                        market_data = json.load(f)
                    with metrics_path.open("r", encoding="utf-8") as f:
                        metrics_data = json.load(f)
                        
                    company_name = market_data.get("company_name", ticker)
                    currency = market_data.get("currency", "원" if is_valid_kr_ticker(ticker) else "달러")
                    
                    combined_data["companies"][ticker] = {
                        "company_name": company_name,
                        "currency": currency,
                        "market_data": market_data,
                        "metrics": metrics_data
                    }
                    print(f"  [MERGE] Merged {ticker} ({company_name}) data.")
                except Exception as e:
                    print(f"  [ERROR] Failed to merge {ticker}: {e}")
                    
    combined_file = valuation_dir / "combined_portfolio_valuation.json"
    try:
        with combined_file.open("w", encoding="utf-8") as f:
            json.dump(combined_data, f, ensure_ascii=False, indent=2)
        print(f"\n[OK] Combined portfolio valuation JSON created successfully at:\n     {combined_file}")
    except Exception as e:
        print(f"\n[ERROR] Failed to save combined JSON: {e}")


def main():
    portfolio = load_portfolio_from_sheet()
    
    kr_targets = []
    us_targets = []
    
    for row in portfolio:
        _, name, currency, raw_code = row
        code = clean_ticker(raw_code)
        
        if currency == "원" and is_valid_kr_ticker(code):
            kr_targets.append((code, name))
        elif currency == "달러" and is_valid_us_ticker(code):
            us_targets.append((code, name))
        else:
            print(f"[SKIP] Non-stock item: {name} ({raw_code}) - Currency: {currency}")
            
    print(f"\n[SUMMARY] Classification Complete:")
    print(f"  - KR Stocks: {len(kr_targets)} items")
    print(f"  - US Stocks: {len(us_targets)} items")
    
    # 1. 한국 주식 5개년 일괄 수집
    print(f"\n{'-'*30} KR STOCKS BATCH START {'-'*30}")
    # 2021년~2025년 연간(A) 및 2026년 1분기(Q1)
    kr_periods = [
        (2021, "A"), (2022, "A"), (2023, "A"), (2024, "A"), (2025, "A"), (2026, "Q1")
    ]
    kr_success = 0
    kr_total = len(kr_targets) * len(kr_periods)
    kr_count = 0
    
    for ticker, name in kr_targets:
        for year, quarter in kr_periods:
            kr_count += 1
            print(f"\n[RUN] [{kr_count}/{kr_total}] {name} ({ticker}) -- {year} {quarter}")
            try:
                run_pipeline(ticker, year, quarter)
                kr_success += 1
            except SystemExit:
                print(f"[SKIP] {name} ({ticker}) {year} {quarter} - Data unavailable")
            except Exception as e:
                print(f"[ERROR] {name} ({ticker}) {year} {quarter} failed: {e}")

    # 2. 미국 주식 5개년 일괄 수집
    print(f"\n{'-'*30} US STOCKS BATCH START {'-'*30}")
    # 2021년~2025년 연간(A)
    us_periods = [
        (2021, "A"), (2022, "A"), (2023, "A"), (2024, "A"), (2025, "A")
    ]
    us_success = 0
    us_total = len(us_targets) * len(us_periods)
    us_count = 0
    
    for ticker, name in us_targets:
        for year, quarter in us_periods:
            us_count += 1
            print(f"\n[RUN] [{us_count}/{us_total}] {name} ({ticker}) -- {year} {quarter}")
            try:
                res = run_us_pipeline(ticker, year, quarter)
                if res:
                    us_success += 1
                else:
                    print(f"[SKIP] {name} ({ticker}) {year} {quarter} - No data")
            except Exception as e:
                print(f"[ERROR] {name} ({ticker}) {year} {quarter} failed: {e}")
                
    print(f"\n{'='*60}")
    print(f"BATCH PROCESS COMPLETE!")
    print(f"  - KR Stocks Success: {kr_success}/{kr_total}")
    print(f"  - US Stocks Success: {us_success}/{us_total}")
    print(f"{'='*60}")
    
    # 3. 통합 JSON 파일 빌드
    create_combined_json()


if __name__ == "__main__":
    main()
