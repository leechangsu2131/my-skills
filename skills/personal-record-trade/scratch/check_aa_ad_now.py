import gspread
import sys

sys.path.append(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\personal-record-trade")
from gsheet_auth import get_client, get_sheet_id

gc = get_client()
ss = gc.open_by_key(get_sheet_id())
ws = ss.worksheet('🎯 비중조절신호')

records = ws.get_all_values()
for i, r in enumerate(records[:15]):
    aa = r[26] if len(r)>26 else ""
    ab = r[27] if len(r)>27 else ""
    ac = r[28] if len(r)>28 else ""
    ad = r[29] if len(r)>29 else ""
    print(f"Row {i+1}: AA=[{aa}], AB=[{ab}], AC=[{ac}], AD=[{ad}]")
