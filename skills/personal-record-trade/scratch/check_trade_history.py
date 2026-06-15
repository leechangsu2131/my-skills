import gspread
import sys

sys.path.append(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\personal-record-trade")
from gsheet_auth import get_client, get_sheet_id

gc = get_client()
ss = gc.open_by_key(get_sheet_id())
ws = ss.worksheet('매매내역')

records = ws.get_all_values()

print(f"Total rows in 매매내역: {len(records)}")
print("--- Last 20 records ---")
# Print headers
if records:
    print("Header:", records[0])

# Print last 20 rows
for row in records[-20:]:
    print(row)
