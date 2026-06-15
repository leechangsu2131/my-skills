import gspread
import sys

sys.path.append(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\personal-record-trade")
from gsheet_auth import get_client, get_sheet_id

gc = get_client()
ss = gc.open_by_key(get_sheet_id())
ws = ss.worksheet('📒 매매일지')

records = ws.get_all_values()

print(f"Total rows in 📒 매매일지: {len(records)}")
print("--- Last 10 records ---")
if records:
    print("Header:", records[0])
    if len(records) > 1:
        print("Header2:", records[1])

for row in records[-10:]:
    print(row)
