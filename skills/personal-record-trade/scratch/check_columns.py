import gspread
import sys

sys.path.append(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\personal-record-trade")
from gsheet_auth import get_client, get_sheet_id

gc = get_client()
ss = gc.open_by_key(get_sheet_id())
ws = ss.worksheet('🎯 비중조절신호')
records = ws.get_all_values(value_render_option='FORMULA')

for i, r in enumerate(records[:15]):
    y_val = r[24] if len(r) > 24 else ""
    z_val = r[25] if len(r) > 25 else ""
    aa_val = r[26] if len(r) > 26 else ""
    ab_val = r[27] if len(r) > 27 else ""
    print(f"Row {i+1}: Y={y_val}, Z={z_val}, AA={aa_val}, AB={ab_val}")
