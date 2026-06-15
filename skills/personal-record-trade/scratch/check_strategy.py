import gspread
import sys

sys.path.append(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\personal-record-trade")
from gsheet_auth import get_client, get_sheet_id

gc = get_client()
ss = gc.open_by_key(get_sheet_id())
ws = ss.worksheet('🧠 전략·전망')

records = ws.get_all_values()

print(f"Total rows in 🧠 전략·전망: {len(records)}")
print(f"Total cols: {len(records[0]) if records else 0}")
print()

# Print all rows to understand the structure
for i, row in enumerate(records[:30]):
    print(f"Row {i+1}: {row}")
