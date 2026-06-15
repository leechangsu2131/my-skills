import gspread
import sys
from collections import defaultdict
from datetime import datetime
import re

sys.path.append(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\personal-record-trade")
from gsheet_auth import get_client, get_sheet_id

gc = get_client()
ss = gc.open_by_key(get_sheet_id())
ws = ss.worksheet('📒 매매일지')
records = ws.get_all_values()

# Headers: ['매매일', '포지션ID', '티커', '종목명', '구분', '수량', '금액(원)', '매매근거', ...]
# Start from row 4 (index 3)
trades = records[3:]

# Group by Stock Name
stock_trades = defaultdict(list)

for idx, row in enumerate(trades):
    if not row or len(row) < 4: continue
    date_str = row[0].strip()
    pos_id = row[1].strip()
    name = row[3].strip()
    buy_sell = row[4].strip() if len(row) > 4 else ""
    
    # Try to parse date
    try:
        # Expected format: "YYYY. MM. DD" or similar
        clean_date = re.sub(r'[^\d.]', '', date_str)
        parts = [p for p in clean_date.split('.') if p]
        if len(parts) >= 3:
            dt = datetime(int(parts[0]), int(parts[1]), int(parts[2]))
            stock_trades[name].append({
                'row_idx': idx + 4, # 1-indexed
                'date': dt,
                'pos_id': pos_id,
                'type': buy_sell
            })
    except Exception as e:
        continue

print("--- Sample groupings (Top 5 stocks by trade count) ---")
sorted_stocks = sorted(stock_trades.items(), key=lambda x: len(x[1]), reverse=True)
for name, tr_list in sorted_stocks[:5]:
    print(f"\n[{name}] - {len(tr_list)} trades")
    for tr in tr_list[-5:]: # show last 5 trades for this stock
        print(f"  Row {tr['row_idx']}: {tr['date'].strftime('%Y-%m-%d')} | {tr['type']} | Current ID: '{tr['pos_id']}'")
