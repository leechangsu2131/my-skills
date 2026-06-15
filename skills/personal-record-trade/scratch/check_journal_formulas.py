import gspread
import sys

sys.path.append(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\personal-record-trade")
from gsheet_auth import get_client, get_sheet_id

gc = get_client()
ss = gc.open_by_key(get_sheet_id())
ws = ss.worksheet('📒 매매일지')

records = ws.get_all_values(value_render_option='FORMULA')

print("--- Formulas in 📒 매매일지 ---")
for i in range(10):
    if i < len(records):
        print(f"Row {i+1}: {records[i]}")
