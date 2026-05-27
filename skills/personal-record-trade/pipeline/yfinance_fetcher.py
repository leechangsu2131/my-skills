import sys

try:
    import yfinance as yf
except ImportError:
    print("yfinance 라이브러리가 설치되어 있지 않습니다.")
    print("설치: pip install yfinance")
    sys.exit(1)

def get_yfinance_metrics(ticker: str, year: int, quarter: str = "A"):
    """
    yfinance를 사용하여 해당 종목의 특정 연도/분기 지표를 추출합니다.
    """
    # 한국 주식인 경우 .KS 또는 .KQ가 붙어야 함
    if not ticker.endswith(".KS") and not ticker.endswith(".KQ"):
        # 거래소 구분 로직이 복잡하므로 일단 코스피(.KS)로 시도
        yf_ticker_str = f"{ticker}.KS"
    else:
        yf_ticker_str = ticker
        
    print(f"[{ticker}] yfinance 데이터 수집 중... ({year} {quarter})")
    try:
        yf_ticker = yf.Ticker(yf_ticker_str)
        is_quarterly = quarter != "A"
        
        if is_quarterly:
            inc = yf_ticker.quarterly_financials
            bs = yf_ticker.quarterly_balance_sheet
            cf = yf_ticker.quarterly_cashflow
            # 분기 매핑 로직 (간단히 해당 연도의 해당 분기 월 찾기)
            # Q1: 3월, H1: 6월, Q3: 9월
            month = 3 if quarter == "Q1" else (6 if quarter == "H1" else 9)
            cols = [c for c in inc.columns if c.year == year and c.month == month]
        else:
            inc = yf_ticker.financials
            bs = yf_ticker.balance_sheet
            cf = yf_ticker.cashflow
            cols = [c for c in inc.columns if c.year == year]
            
        if not cols:
            print(f"[경고] yfinance에서 {year}년 {quarter}에 해당하는 리포트를 찾을 수 없습니다.")
            return None
            
        col = cols[0]
        
        def safe_get(df, key):
            try:
                if key in df.index:
                    val = df.loc[key, col]
                    if val is not None and str(val) != 'nan':
                        return float(val)
            except:
                pass
            return 0.0

        eq_val = safe_get(bs, 'Stockholders Equity')
        if eq_val == 0.0:
            eq_val = safe_get(bs, 'Total Equity Gross Minority Interest')

        yf_data = {
            "revenue": safe_get(inc, 'Total Revenue'),
            "operating_income": safe_get(inc, 'Operating Income'),
            "net_income": safe_get(inc, 'Net Income'),
            "total_equity": eq_val,
            "cash": safe_get(bs, 'Cash And Cash Equivalents'),
            "op_cashflow": safe_get(cf, 'Operating Cash Flow'),
            "capex": abs(safe_get(cf, 'Capital Expenditure')),
            "eps": safe_get(inc, 'Basic EPS'),
            # yfinance에서 누락되기 쉬운 항목은 0.0으로 처리
            "short_debt": safe_get(bs, 'Current Debt'),
            "long_debt": safe_get(bs, 'Long Term Debt'),
            "ebit": safe_get(inc, 'EBIT'),
            "tax_rate": 0.22  # DART와 동일하게
        }
        
        return yf_data
        
    except Exception as e:
        print(f"[오류] yfinance 데이터 수집 실패: {e}")
        return None

if __name__ == "__main__":
    res = get_yfinance_metrics("000660", 2024, "A")
    print(res)
