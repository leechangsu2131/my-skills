import gspread
import sys

sys.path.append(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\personal-record-trade")
from gsheet_auth import get_client, get_sheet_id

gc = get_client()
ss = gc.open_by_key(get_sheet_id())
ws = ss.worksheet('🎯 비중조절신호')

# Clear everything in AA~AD from row 7 downwards to ensure no overlap with Dashboard (AA1:AD6)
updates = [
    {'range': 'AA7:AD200', 'values': [[''] * 4 for _ in range(194)]}
]

ws.batch_update(updates, value_input_option='USER_ENTERED')
print("Cleared AA7:AD200 to remove any leftover garbage below the dashboard.")
