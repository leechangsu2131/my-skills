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
trades = records[3:]
stock_trades = defaultdict(list)

# 1. Parse and group by stock
for idx, row in enumerate(trades):
    if not row or len(row) < 4: continue
    date_str = row[0].strip()
    name = row[3].strip()
    if not date_str or not name: continue
    
    try:
        clean_date = re.sub(r'[^\d.]', '', date_str)
        parts = [p for p in clean_date.split('.') if p]
        if len(parts) >= 3:
            # Handle 2-digit years if present, though format is YYYY
            yy = int(parts[0])
            if yy < 100: yy += 2000
            dt = datetime(yy, int(parts[1]), int(parts[2]))
            stock_trades[name].append({
                'row_idx': idx + 4, # 1-indexed
                'date': dt
            })
    except Exception:
        continue

def get_season(month):
    if month in [3, 4, 5]: return '봄'
    if month in [6, 7, 8]: return '여름'
    if month in [9, 10, 11]: return '가을'
    return '겨울'

updates = []

# 2. Cluster by 60-day gap and assign names
for stock, tr_list in stock_trades.items():
    tr_list.sort(key=lambda x: x['date'])
    groups = []
    current_group = []
    
    for tr in tr_list:
        if not current_group:
            current_group.append(tr)
        else:
            last_tr = current_group[-1]
            gap = (tr['date'] - last_tr['date']).days
            if gap > 60:
                groups.append(current_group)
                current_group = [tr]
            else:
                current_group.append(tr)
    if current_group:
        groups.append(current_group)

    # Naming
    for group in groups:
        first_date = group[0]['date']
        yy = first_date.strftime('%y')
        season = get_season(first_date.month)
        base_name = f"{stock}-{yy}년{season}"
        
        for tr in group:
            updates.append({'range': f'B{tr["row_idx"]}', 'values': [[base_name]]})

# 3. Batch Update
if updates:
    # Google Sheets limits batch update items, but ~300 is fine.
    ws.batch_update(updates, value_input_option='USER_ENTERED')
    print(f"Successfully applied semantic Position IDs to {len(updates)} rows.")
else:
    print("No rows to update.")
