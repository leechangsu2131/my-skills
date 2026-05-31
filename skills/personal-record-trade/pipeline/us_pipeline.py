"""
미국 개별주 파이프라인 — yfinance 전용
DART API 없이 yfinance만으로 재무제표 + 시장 데이터를 수집하여
한국주와 동일한 metrics.json / market.json 포맷으로 저장합니다.
"""
import sys
import os
import json
from pathlib import Path
from datetime import datetime

# Windows cp949 인코딩 오류 방지
if hasattr(sys.stdout, 'reconfigure'):
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    import yfinance as yf
except ImportError:
    print("yfinance 라이브러리가 필요합니다: pip install yfinance")
    sys.exit(1)


def _safe_get(df, key, col):
    """DataFrame에서 안전하게 값을 추출합니다."""
    try:
        if key in df.index:
            val = df.loc[key, col]
            if val is not None and str(val) != 'nan':
                return float(val)
    except Exception:
        pass
    return None


def fetch_us_market_data(ticker_str: str) -> dict | None:
    """yfinance에서 미국주 시장 데이터(주가, 시총, 발행주식수)를 수집합니다."""
    try:
        t = yf.Ticker(ticker_str)
        info = t.info
        
        price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
        market_cap = info.get("marketCap")
        shares = info.get("sharesOutstanding")
        
        fwd_pe_val = info.get("forwardPE")
        forward_pe = fwd_pe_val or ""
        
        target_price = info.get("targetMeanPrice")
        
        try:
            from pipeline.layer1_store import save_row
            yahoo_data = {}
            if fwd_pe_val:
                yahoo_data["fwd_pe_ntm"] = round(fwd_pe_val, 4)
            if target_price:
                yahoo_data["fair_value"] = round(target_price, 4)
                
            # 추가 밸류에이션 지표들 추출
            pe_val = info.get("trailingPE")
            if pe_val:
                yahoo_data["pe_ratio"] = round(pe_val, 4)
            ps_val = info.get("priceToSalesTrailing12Months")
            if ps_val:
                yahoo_data["ps_ratio"] = round(ps_val, 4)
            pb_val = info.get("priceToBook")
            if pb_val:
                yahoo_data["pb_ratio"] = round(pb_val, 4)
            ev_ebitda = info.get("enterpriseToEbitda")
            if ev_ebitda:
                yahoo_data["ev_ebitda"] = round(ev_ebitda, 4)
            op_margin_val = info.get("operatingMargins")
            if op_margin_val is not None:
                yahoo_data["op_margin"] = round(op_margin_val * 100.0, 4)

            if yahoo_data:
                save_row(ticker_str, "yahoo", yahoo_data)
        except Exception as e:
            print(f"Layer 1 저장 실패: {e}")
            
        name = info.get("shortName") or info.get("longName") or ticker_str
        currency = info.get("currency", "USD")
        
        if not price:
            print(f"[경고] {ticker_str}: 주가 정보를 가져올 수 없습니다.")
            return None
        
        return {
            "ticker": ticker_str,
            "company_name": name,
            "historical_average_per": 20.0,
            "peer_average_per": 20.0,
            "forward_pe": forward_pe,
            "currency": info.get("currency", "USD"),
            "price": price,
            "shares_outstanding": shares,
            "market_cap": market_cap,
            "valuation_date": datetime.today().strftime("%Y-%m-%d"),
            "market_data_as_of": str(os.popen('date /t').read().strip()),
        }
    except Exception as e:
        print(f"[오류] {ticker_str} 시장 데이터 수집 실패: {e}")
        return None


def fetch_us_financials(ticker_str: str, year: int, quarter: str = "A") -> list | None:
    """
    yfinance에서 미국주 재무제표를 수집하여 metrics.json 형태로 매핑합니다.
    """
    try:
        t = yf.Ticker(ticker_str)
        is_quarterly = quarter != "A"
        
        if is_quarterly:
            inc = t.quarterly_financials
            bs = t.quarterly_balance_sheet
            cf = t.quarterly_cashflow
            month_map = {"Q1": 3, "H1": 6, "Q3": 9}
            target_month = month_map.get(quarter, 3)
            cols = [c for c in inc.columns if c.year == year and c.month == target_month]
        else:
            inc = t.financials
            bs = t.balance_sheet
            cf = t.cashflow
            cols = [c for c in inc.columns if c.year == year]
        
        if not cols:
            print(f"[경고] {ticker_str}: {year}{quarter} 데이터를 yfinance에서 찾을 수 없습니다.")
            print(f"  사용 가능한 날짜: {list(inc.columns)}")
            return None
        
        col = cols[0]
        
        # BS 컬럼은 inc와 다를 수 있으므로 별도 탐색
        bs_cols = [c for c in bs.columns if c.year == year]
        if is_quarterly:
            bs_cols = [c for c in bs.columns if c.year == year and c.month == target_month]
        bs_col = bs_cols[0] if bs_cols else col
        
        cf_cols = [c for c in cf.columns if c.year == year]
        if is_quarterly:
            cf_cols = [c for c in cf.columns if c.year == year and c.month == target_month]
        cf_col = cf_cols[0] if cf_cols else col
        
        # 지표 추출
        revenue = _safe_get(inc, 'Total Revenue', col) or 0
        op_income = _safe_get(inc, 'Operating Income', col) or 0
        net_income = _safe_get(inc, 'Net Income', col) or 0
        ebit = _safe_get(inc, 'EBIT', col) or op_income
        eps = _safe_get(inc, 'Basic EPS', col) or 0
        
        total_equity = _safe_get(bs, 'Stockholders Equity', bs_col) or _safe_get(bs, 'Total Equity Gross Minority Interest', bs_col) or 0
        cash = _safe_get(bs, 'Cash And Cash Equivalents', bs_col) or 0
        short_debt = _safe_get(bs, 'Current Debt', bs_col) or 0
        long_debt = _safe_get(bs, 'Long Term Debt', bs_col) or 0
        
        op_cashflow = _safe_get(cf, 'Operating Cash Flow', cf_col) or 0
        capex = abs(_safe_get(cf, 'Capital Expenditure', cf_col) or 0)
        
        # 파생 지표
        fcf = op_cashflow - capex
        net_debt = short_debt + long_debt - cash
        tax_rate = 0.21  # 미국 법인세율
        
        period_str = f"{year}{quarter}"
        
        mapped_dict = {
            "revenue": ("Revenue", revenue),
            "operating_income": ("Operating Income", op_income),
            "net_income": ("Net Income", net_income),
            "eps": ("EPS", eps),
            "ebit": ("EBIT", ebit),
            "tax_rate": ("Tax Rate", tax_rate),
            "op_cashflow": ("Operating Cash Flow", op_cashflow),
            "capex": ("Capital Expenditures", capex),
            "fcf": ("Free Cash Flow", fcf),
            "total_equity": ("Total Equity", total_equity),
            "cash": ("Cash and Cash Equivalents", cash),
            "short_debt": ("Short-Term Debt", short_debt),
            "long_debt": ("Long-Term Debt", long_debt),
            "net_debt": ("Net Debt", net_debt),
        }
        
        metrics = []
        for key, (label, val) in mapped_dict.items():
            metrics.append({
                "metric_key": key,
                "label": label,
                "value": float(val) if key == "tax_rate" else (float(val) if val else 0),
                "unit": "ratio" if key == "tax_rate" else ("USD/share" if key == "eps" else "USD"),
                "period": period_str,
                "source_method": "market",
                "report_year": str(year),
                "statement_name": "yfinance (US GAAP)",
                "original_account_name": key,
                "original_amount": val,
                "yf_value": None,  # yfinance가 원본이므로 비교 대상 없음
                "confidence": 0.9,
                "note": f"yfinance direct fetch for {ticker_str} {year} {quarter}"
            })
        
        return metrics
        
    except Exception as e:
        print(f"[오류] {ticker_str} 재무 데이터 수집 실패: {e}")
        return None


def run_us_pipeline(ticker_str: str, year: int, quarter: str = "A"):
    """미국주 단일 종목 파이프라인 실행"""
    print("========================================")
    print(f"US 파이프라인 가동 (종목: {ticker_str}, 연도: {year}, 분기: {quarter})")
    print("========================================")
    
    # 1. Market Data
    print(f"\n[단계 1/3] 시장 데이터 수집...")
    market = fetch_us_market_data(ticker_str)
    if not market:
        print("[실패] 시장 데이터를 수집하지 못했습니다.")
        return False
    print(f"  [성공] {market['company_name']} - ${market['price']:,.2f} (시총: ${market.get('market_cap', 0):,.0f})")
    
    # 2. Financials
    print(f"\n[단계 2/3] yfinance 재무제표 수집 ({year}{quarter})...")
    metrics = fetch_us_financials(ticker_str, year, quarter)
    if not metrics:
        print("[건너뜀] 해당 기간 재무 데이터 없음")
        return False
    
    # 3. Save
    print(f"\n[단계 3/3] 저장...")
    from pipeline.generator import save_valuation_data
    save_valuation_data(ticker_str, market, metrics)
    
    print(f"\n[완료] {ticker_str} 파이프라인 완료!")
    return True


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    if len(sys.argv) < 3:
        print("사용법: python us_pipeline.py <TICKER> <YEAR> [QUARTER]")
        print("예시: python us_pipeline.py NVDA 2025 A")
        sys.exit(1)
    
    ticker = sys.argv[1]
    year = int(sys.argv[2])
    quarter = sys.argv[3] if len(sys.argv) > 3 else "A"
    run_us_pipeline(ticker, year, quarter)
