import sys
from gsheet_auth import get_client, get_sheet_id

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

client = get_client()
doc = client.open_by_key(get_sheet_id())
ws_journal = doc.worksheet("📒 매매일지")
ws_signal = doc.worksheet("🎯 비중조절신호")

trades = [
    {
        "date": "2026. 05. 29",
        "ticker": "453850",
        "name": "ACE 중국과창판STAR50(합성)",
        "type": "매수",
        "qty": 497,
        "price": 14477,
        "amount": 497 * 14477
    },
    {
        "date": "2026. 05. 29",
        "ticker": "486290",
        "name": "TIGER TSMC파운드리밸류체인",
        "type": "매수",
        "qty": 257,
        "price": 38780,
        "amount": 257 * 38780
    },
    {
        "date": "2026. 06. 05",
        "ticker": "000660",
        "name": "SK하이닉스",
        "type": "매수",
        "qty": 2,
        "price": 2142000,
        "amount": 2 * 2142000
    },
    {
        "date": "2026. 06. 05",
        "ticker": "042700",
        "name": "한미반도체",
        "type": "매수",
        "qty": 10,
        "price": 294000,
        "amount": 10 * 294000
    }
]

# 1. Append to 매매일지
rows_to_append = []
for t in trades:
    row = [
        t["date"], t["ticker"], t["name"], t["type"], t["qty"], 
        f"{t['price']:,}", f"{t['amount']:,}", "", "", "", "", "", "", ""
    ]
    rows_to_append.append(row)

ws_journal.append_rows(rows_to_append, value_input_option='USER_ENTERED')
print(f"Successfully appended {len(rows_to_append)} rows to 매매일지.")

# 2. Update 🎯 비중조절신호 (Portfolio)
signal_data = ws_signal.get_all_values()
# Find rows for each ticker
ticker_col_idx = 1 # Column B (0-indexed)
qty_col_idx = 20 # Column U (0-indexed)
price_col_idx = 5 # Column F (0-indexed)

for t in trades:
    found = False
    for i, row in enumerate(signal_data):
        if len(row) > ticker_col_idx and row[ticker_col_idx] == t["ticker"]:
            found = True
            row_idx = i + 1
            # Current values
            try:
                curr_qty = int(row[qty_col_idx].replace(',', '')) if len(row) > qty_col_idx and row[qty_col_idx] else 0
            except ValueError:
                curr_qty = 0
                
            try:
                curr_price = float(row[price_col_idx].replace(',', '')) if len(row) > price_col_idx and row[price_col_idx] else 0
            except ValueError:
                curr_price = 0
            
            # New quantity
            new_qty = curr_qty + t["qty"]
            
            # New average price = (curr_qty * curr_price + trade_qty * trade_price) / new_qty
            if new_qty > 0:
                new_avg_price = ((curr_qty * curr_price) + t["amount"]) / new_qty
            else:
                new_avg_price = curr_price
                
            # Update sheet
            ws_signal.update_cell(row_idx, qty_col_idx + 1, new_qty)
            ws_signal.update_cell(row_idx, price_col_idx + 1, new_avg_price)
            print(f"Updated Portfolio for {t['name']}: Qty {curr_qty}->{new_qty}, Avg Price {curr_price}->{new_avg_price}")
            break
            
    if not found:
        print(f"Ticker {t['ticker']} ({t['name']}) not found in 🎯 비중조절신호. Quantity not updated.")

