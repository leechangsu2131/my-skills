import gspread
import sys

sys.path.append(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\personal-record-trade")
from gsheet_auth import get_client, get_sheet_id

gc = get_client()
ss = gc.open_by_key(get_sheet_id())
ws = ss.worksheet('📒 매매일지')

records = ws.get_all_values()
headers = records[2] if len(records) > 2 else []
print(f"Headers: {headers}")

# Find rows to delete (empty entries for 6. 8)
rows_to_delete = []
for i, row in enumerate(records):
    if len(row) > 0 and '2026. 6. 8' in row[0] and row[4] == '':
        rows_to_delete.append(i + 1) # 1-indexed

print(f"Rows to delete: {rows_to_delete}")
