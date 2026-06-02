import gspread
import sys

sys.path.append(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\personal-record-trade")
from gsheet_auth import get_client, get_sheet_id

gc = get_client()
ss = gc.open_by_key(get_sheet_id())
ws = ss.worksheet('🎯 비중조절신호')

records = ws.get_all_values(value_render_option='FORMULA')

print("--- Current State of PoC Columns ---")
for i in [3, 4, 11, 12]: # Row indices 3(Headers), 4(GOOG), 11(PLTR), 12(현대해상)
    r = records[i]
    name = r[1] if len(r)>1 else ""
    z = r[25] if len(r)>25 else ""
    aa = r[26] if len(r)>26 else ""
    ab = r[27] if len(r)>27 else ""
    o = r[14] if len(r)>14 else ""
    print(f"Row {i+1} ({name}): O=[{o}], Z=[{z}], AA=[{aa}], AB=[{ab}]")
