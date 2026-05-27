import sys
from datetime import datetime

try:
    from pykrx import stock
except ImportError:
    print("pykrx 라이브러리가 설치되어 있지 않습니다. 한국 주식 데이터 수집에 필요합니다.")
    print("설치: pip install pykrx")
    sys.exit(1)

def get_market_data(ticker: str):
    """
    pykrx를 통해 종목의 현재(최근) 주가, 시가총액, 발행주식수를 수집합니다.
    """
    today = datetime.today().strftime("%Y%m%d")
    print(f"[{ticker}] 최신 시장 데이터 수집 중 (기준일: {today})...")
    
    try:
        # 최근 영업일 기준 시가총액 정보 가져오기
        df = stock.get_market_cap(today, today, ticker)
        if df.empty:
            # 주말/휴일일 경우 최근 5일 중 가장 마지막 거래일을 가져오기 위해 범위 확장
            import datetime as dt
            start_date = (datetime.today() - dt.timedelta(days=7)).strftime("%Y%m%d")
            df = stock.get_market_cap(start_date, today, ticker)
            
        if df.empty:
            print("[오류] 주가 데이터를 가져오지 못했습니다. (빈 데이터)")
            raise ValueError("Empty dataframe from pykrx")
            
        # 가장 최근 일자 데이터
        latest_data = df.iloc[-1]
        
        # ticker에 따른 회사 이름
        company_name = stock.get_market_ticker_name(ticker)
        
        market_info = {
            "ticker": ticker,
            "company_name": company_name,
            "valuation_date": datetime.today().strftime("%Y-%m-%d"),
            "market_data_as_of": df.index[-1].strftime("%Y-%m-%d"),
            "price": int(latest_data['시가총액'] / latest_data['상장주식수']),
            "shares_outstanding": int(latest_data['상장주식수']),
            "market_cap": int(latest_data['시가총액']),
            # TODO: 과거 PER이나 Peer PER은 추가 로직 필요 (임시 고정값)
            "historical_average_per": 15.0,
            "peer_average_per": 15.0,
            "current_tam": 40000000000000,
            "projected_tam_5yr": 60000000000000,
            "currency": "KRW",
            "note": "Auto-fetched via pykrx"
        }
        
        return market_info

    except Exception as e:
        print(f"[오류] pykrx 주가 데이터 수집 실패: {e}")
        print("[알림] 야후 파이낸스(yfinance)를 통해 실시간 주가 수집을 시도합니다.")
        try:
            import yfinance as yf
            ticker_yf = f"{ticker}.KS"
            stock_info = yf.Ticker(ticker_yf)
            info = stock_info.info
            
            price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
            market_cap = info.get("marketCap")
            shares = info.get("sharesOutstanding")
            
            if not price:
                raise ValueError("yfinance에서 가격 정보를 가져오지 못했습니다.")
                
            print(f"✅ yfinance 실시간 주가 수집 성공: {int(price):,} 원")
            return {
                "ticker": ticker,
                "company_name": info.get("longName", "SK하이닉스" if ticker == "000660" else f"종목({ticker})"),
                "valuation_date": datetime.today().strftime("%Y-%m-%d"),
                "market_data_as_of": datetime.today().strftime("%Y-%m-%d"),
                "price": int(price),
                "shares_outstanding": int(shares) if shares else 728000000,
                "market_cap": int(market_cap) if market_cap else int(price * (shares or 728000000)),
                "historical_average_per": 15.0,
                "peer_average_per": 15.0,
                "current_tam": 40000000000000,
                "projected_tam_5yr": 60000000000000,
                "currency": "KRW",
                "note": "Auto-fetched via yfinance"
            }
        except Exception as e_yf:
            print(f"[오류] yfinance 수집도 실패했습니다: {e_yf}")
            print("[알림] 최후의 수단으로 수동(Fallback) 데이터를 사용합니다.")
            return {
                "ticker": ticker,
                "company_name": "SK하이닉스" if ticker == "000660" else f"종목({ticker})",
                "valuation_date": datetime.today().strftime("%Y-%m-%d"),
                "market_data_as_of": datetime.today().strftime("%Y-%m-%d"),
                "price": 2250000 if ticker == "000660" else 100000,
                "shares_outstanding": 728000000 if ticker == "000660" else 10000000,
                "market_cap": (2250000 * 728000000) if ticker == "000660" else 1000000000000,
                "historical_average_per": 15.0,
                "peer_average_per": 15.0,
                "current_tam": 40000000000000,
                "projected_tam_5yr": 60000000000000,
                "currency": "KRW",
                "note": "Fallback data used due to pykrx and yfinance error"
            }

if __name__ == "__main__":
    res = get_market_data("009150")
    print(res)
