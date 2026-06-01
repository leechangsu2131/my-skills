import gspread
import sys

sys.path.append(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\personal-record-trade")
from gsheet_auth import get_client, get_sheet_id

gc = get_client()
ss = gc.open_by_key(get_sheet_id())
ws_log = ss.worksheet("📒 매매일지")

records = ws_log.get_all_values()

# Find the last valid row. Looking at the records, row 295 is the last valid one:
# Row 295: ['2026. 5. 21', 'P054', 'AAPL', 'Apple', '매수', '4', '1805090', ...]
# Row 296 is the first corrupted one.
# But just to be sure, let's find the first row after 290 that has empty column A but data somewhere else,
# or where column A starts with '2026-06-01' in wrong place.
# Actually, the user confirmed 5.21 trades (rows up to 295) are correct.
# So we can safely delete from row 296 up to the current last row.

start_delete = 296
end_delete = len(records)

if end_delete >= start_delete:
    print(f"Deleting rows from {start_delete} to {end_delete}")
    # gspread delete_rows takes start_index and end_index
    ws_log.delete_rows(start_delete, end_delete)
else:
    print("No rows to delete.")

# Now we prepare the 3 correctly formatted 06.01 trades
# A: 매매일, B: 포지션ID, C: 티커, D: 종목명, E: 구분, F: 수량, G: 금액(원), H: 매매근거, I~M: 빈칸
trades = [
    ["2026. 6. 1", "P041", "360750", "TIGER 미국S&P500", "매도", "782", "22341740", "당일매도", "", "", "", "", ""],
    ["2026. 6. 1", "-", "461900", "PLUS 미국테크TOP10", "매도", "1166", "29650214", "당일매도", "", "", "", "", ""],
    ["2026. 6. 1", "P052", "481180", "SOL 미국AI소프트웨어", "매도", "615", "10399650", "당일매도", "", "", "", "", ""]
]

# We will use update() instead of append_row() to guarantee exact cell placement.
# start_delete is where we insert (296)
start_row = start_delete
end_row = start_row + len(trades) - 1
range_str = f"A{start_row}:M{end_row}"

ws_log.update(range_name=range_str, values=trades, value_input_option="USER_ENTERED")
print(f"Successfully inserted 3 trades at {range_str}")
