import gspread
import sys
import datetime

sys.path.append(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\personal-record-trade")
from gsheet_auth import get_client, get_sheet_id

gc = get_client()
ss = gc.open_by_key(get_sheet_id())
ws_log = ss.worksheet("📒 매매일지")

all_records = ws_log.get_all_values()
rows_to_delete = []
for i, row in enumerate(all_records):
    # Find the wrongly added entries for '2026. 6. 1' (or '2026-06-01') which have wrong format
    # Specifically, they have "당일매도" in H column or "28570" in F column (qty) etc.
    if len(row) > 7 and '2026. 6. 1' in row[0] and row[4] in ['782', '1166', '615']: 
        # Since I messed up, the 'qty' got put into the 'type' column (index 4)
        rows_to_delete.append(i + 1)
    
    # Also I appended 06-01 entries in run_trades.py, which might be in YYYY-MM-DD format
    if len(row) > 7 and '2026-06-01' in row[0]:
        rows_to_delete.append(i + 1)

# Unique list and sort reverse
rows_to_delete = sorted(list(set(rows_to_delete)), reverse=True)

for r in rows_to_delete:
    print(f"Deleting wrongly formatted row {r}")
    ws_log.delete_rows(r)

# Correctly formatted trades for 06.01
# B: 포지션ID, C: 티커, D: 종목명, E: 구분, F: 수량, G: 금액(원), H: 매매근거
trades = [
    {
        "date": "2026-06-01", 
        "position_id": "P041", 
        "ticker": "360750", 
        "name": "TIGER 미국S&P500", 
        "type": "매도", 
        "qty": 782, 
        "amount": 22341740, 
        "reason": "당일매도"
    },
    {
        "date": "2026-06-01", 
        "position_id": "-", 
        "ticker": "461900", 
        "name": "PLUS 미국테크TOP10", 
        "type": "매도", 
        "qty": 1166, 
        "amount": 29650214, 
        "reason": "당일매도"
    },
    {
        "date": "2026-06-01", 
        "position_id": "P052", 
        "ticker": "481180", 
        "name": "SOL 미국AI소프트웨어", 
        "type": "매도", 
        "qty": 615, 
        "amount": 10399650, 
        "reason": "당일매도"
    }
]

def parse_trade(raw: dict) -> list:
    today = datetime.date.today().isoformat()
    return [
        raw.get("date", today),
        raw.get("position_id", ""),  
        raw.get("ticker", ""),
        raw.get("name", ""),
        raw.get("type", ""),
        raw.get("qty", ""),
        raw.get("amount", ""),       
        raw.get("reason", ""),
        raw.get("score", ""),
        raw.get("condition", ""),
        raw.get("analysis", ""),
        raw.get("bias", ""),
        raw.get("fix", ""),
    ]

for t in trades:
    row = parse_trade(t)
    ws_log.append_row(row, value_input_option="USER_ENTERED")
    print(f"Added correct trade: {t['name']}")

print("Fix applied successfully!")
