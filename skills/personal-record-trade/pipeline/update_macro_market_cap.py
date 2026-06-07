import sys
import requests
from bs4 import BeautifulSoup
import yfinance as yf
from pathlib import Path

ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, 'reconfigure'):
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

from gsheet_auth import get_client, get_sheet_id

def get_naver_market_cap(code: str) -> float:
    """Returns total market cap in Trillion KRW (조원)"""
    url = f'https://finance.naver.com/sise/sise_index.naver?code={code}'
    try:
        r = requests.get(url, timeout=10)
        r.encoding = 'euc-kr'
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # <tr><th>시가총액(억)</th><td>21,791,241</td></tr>
        tds = soup.find_all('td')
        for td in tds:
            prev = td.find_previous_sibling('th')
            if prev and '시가총액' in prev.text:
                val_str = td.text.replace(',', '').strip()
                if val_str.isdigit():
                    return float(val_str) / 10000
    except Exception as e:
        print(f"Error fetching {code} market cap from Naver: {e}")
    return 0.0

def get_hybrid_us_market_cap(symbol: str, base_cap_t_usd: float, reference_ticker: str, reference_weight: float) -> float:
    """Returns US index total market cap in Trillion USD, using hybrid approach"""
    try:
        # Option 2: Inverse calculation
        ref_info = yf.Ticker(reference_ticker).info
        ref_market_cap_usd = ref_info.get("marketCap", 0)
        if ref_market_cap_usd > 0:
            inverse_cap_t_usd = (ref_market_cap_usd / reference_weight) / 1e12
            # Cross-check and average (Option 1 + Option 2 hybrid)
            final_cap_t_usd = (base_cap_t_usd + inverse_cap_t_usd) / 2
            print(f"[{symbol}] Base: {base_cap_t_usd}T, Inverse({reference_ticker}): {inverse_cap_t_usd:.1f}T -> Final: {final_cap_t_usd:.1f}T USD")
            return final_cap_t_usd
    except Exception as e:
        print(f"Error computing inverse cap for {symbol}: {e}")
        
    print(f"[{symbol}] Fallback to Base: {base_cap_t_usd}T USD")
    return base_cap_t_usd

def main():
    print("🌍 글로벌 거시 시가총액 스크래핑 봇 가동 (하이브리드 모드)")
    
    # 1. KOSPI, KOSDAQ (in Trillion KRW)
    kospi_krw = get_naver_market_cap('KOSPI')
    if kospi_krw == 0.0:
        raise ValueError("Failed to fetch KOSPI market cap from Naver. Aborting to prevent data corruption.")
        
    kosdaq_krw = get_naver_market_cap('KOSDAQ')
    if kosdaq_krw == 0.0:
        raise ValueError("Failed to fetch KOSDAQ market cap from Naver. Aborting to prevent data corruption.")
        
    print(f"KOSPI: {kospi_krw:.0f} 조원, KOSDAQ: {kosdaq_krw:.0f} 조원")
    
    # 2. Get KRW=X (USD to KRW exchange rate)
    try:
        usdkrw = yf.Ticker("KRW=X").info.get("regularMarketPrice", 1350)
    except:
        usdkrw = 1350
    print(f"실시간 환율 (KRW/USD): {usdkrw:.2f} 원")
    
    # 3. US & Global (in Trillion KRW)
    # S&P 500: Base $45T, AAPL weight ~7%
    sp500_usd = get_hybrid_us_market_cap("S&P 500", 45.0, "AAPL", 0.07)
    
    # NASDAQ: Base $25T, AAPL weight ~8%
    nasdaq_usd = get_hybrid_us_market_cap("NASDAQ", 25.0, "AAPL", 0.08)
    
    # DOW: Base $15T, MSFT weight ~6.5%
    dow_usd = get_hybrid_us_market_cap("DOW", 15.0, "MSFT", 0.065)
    
    # Global (All-World): Base $115T
    global_usd = 115.0
    print(f"[Global] Base: {global_usd}T USD")
    
    # Convert to Trillion KRW (조원)
    # 1 Trillion USD * USDKRW = USDKRW Trillion KRW
    # e.g., 45T USD * 1350 = 60,750T KRW
    sp500_krw = sp500_usd * (usdkrw / 1000) * 1000  # simplified: usd * usdkrw
    nasdaq_krw = nasdaq_usd * usdkrw
    dow_krw = dow_usd * usdkrw
    global_krw = global_usd * usdkrw
    
    # 4. Update Google Sheet (🎯 비중조절신호 K2:P3)
    client = get_client()
    doc = client.open_by_key(get_sheet_id())
    ws = doc.worksheet("🎯 비중조절신호")
    
    headers = ["한국 KOSPI", "한국 KOSDAQ", "미국 S&P 500", "미국 NASDAQ", "미국 DOW", "전세계 Global"]
    values = [kospi_krw, kosdaq_krw, sp500_krw, nasdaq_krw, dow_krw, global_krw]
    
    # Format values as comma-separated strings with "조"
    formatted_values = [f"{int(v):,}" for v in values]
    
    updates = [
        {"range": "K2:P2", "values": [headers]},
        {"range": "K3:P3", "values": [formatted_values]}
    ]
    
    ws.batch_update(updates, value_input_option="USER_ENTERED")
    print("\n✅ 구글 시트 '🎯 비중조절신호' 탭에 성공적으로 업데이트 완료!")
    for h, v in zip(headers, formatted_values):
        print(f" - {h}: {v} 조원")

if __name__ == "__main__":
    main()
