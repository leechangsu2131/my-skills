import gspread
import sys

sys.path.append(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\personal-record-trade")
from gsheet_auth import get_client, get_sheet_id

gc = get_client()
ss = gc.open_by_key(get_sheet_id())

# Also check 👋 청산종목 for status info
ws_closed = ss.worksheet('👋 청산종목')
closed = ws_closed.get_all_values()
print(f"Total rows in 👋 청산종목: {len(closed)}")
for i, row in enumerate(closed[:5]):
    print(f"Row {i+1}: {row}")
print("...")
for i, row in enumerate(closed[-10:]):
    print(f"Row {len(closed)-10+i+1}: {row}")

# Also check 📊 포트폴리오 for current holdings
ws_port = ss.worksheet('📊 포트폴리오')
port = ws_port.get_all_values()
print(f"\nTotal rows in 📊 포트폴리오: {len(port)}")
for i, row in enumerate(port[:20]):
    print(f"Row {i+1}: {row[:6]}")
