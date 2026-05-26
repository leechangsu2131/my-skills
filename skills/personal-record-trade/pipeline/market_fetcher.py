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
            print("[오류] 주가 데이터를 가져오지 못했습니다.")
            return None
            
        # 가장 최근 일자 데이터
        latest_data = df.iloc[-1]
        
        # ticker에 따른 회사 이름
        company_name = stock.get_market_ticker_name(ticker)
        
        market_info = {
            "ticker": ticker,
            "company_name": company_name,
            "valuation_date": datetime.today().strftime("%Y-%m-%d"),
            "market_data_as_of": df.index[-1].strftime("%Y-%m-%d"),
            "price": int(latest_data['종가']),
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
        print(f"[오류] 주가 데이터 수집 실패: {e}")
        return None

if __name__ == "__main__":
    res = get_market_data("009150")
    print(res)
