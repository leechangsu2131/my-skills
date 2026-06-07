import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, 'reconfigure'):
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

from gsheet_auth import get_client, get_sheet_id

def main():
    client = get_client()
    doc = client.open_by_key(get_sheet_id())
    ws = doc.worksheet("🎯 비중조절신호")
    
    # 1. Update Header in AE4
    ws.update_acell('AE4', '시장비중(%)')
    
    tickers = ws.col_values(1)
    names = ws.col_values(2)
    
    updates = []
    
    # Row 1-4 are headers/macros. Data starts at row 7 (index 6 in python 0-based if no empty rows).
    # But let's just loop from row 7 to len(tickers).
    for i in range(6, len(tickers)):
        row = i + 1
        ticker = tickers[i].strip()
        
        # Check name if available
        name = names[i].strip().upper() if i < len(names) else ""
        
        if not ticker or ticker in ["현금", "BTC"]:
            continue
            
        if "ETF" in name:
            print(f"Skipping ETF: {ticker} ({name})")
            continue
            
        # Determine if KR or US
        # KR tickers are exactly 6 characters, mostly digits (e.g., 042700, 005935)
        is_kr = False
        if len(ticker) == 6 and any(c.isdigit() for c in ticker):
            is_kr = True
            
        if is_kr:
            # KRX stock -> Divide by KOSPI (K$3)
            # Add IFERROR to handle temporary Google Finance glitches
            formula = f'=IFERROR(GOOGLEFINANCE(A{row}, "marketcap") / (K$3 * 1000000000000), "")'
        else:
            # US stock -> Divide by S&P 500 (M$3)
            formula = f'=IFERROR(GOOGLEFINANCE(A{row}, "marketcap") * GOOGLEFINANCE("CURRENCY:USDKRW") / (M$3 * 1000000000000), "")'
            
        updates.append({"range": f"AE{row}", "values": [[formula]]})
        print(f"Row {row} [{ticker}]: {formula}")
        
    if updates:
        ws.batch_update(updates, value_input_option="USER_ENTERED")
        print("✅ 성공적으로 시장 보유율(%) 수식을 업데이트했습니다.")
        
        # Add formatting for percentage
        try:
            ws.format(f"AE7:AE{len(tickers)}", {
                "numberFormat": {
                    "type": "PERCENT",
                    "pattern": "0.00%"
                }
            })
            print("✅ 백분율 포맷팅 적용 완료.")
        except Exception as e:
            print(f"포맷팅 경고: {e}")

if __name__ == "__main__":
    main()
