import gspread
import sys

sys.path.append(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\personal-record-trade")
from gsheet_auth import get_client, get_sheet_id

gc = get_client()
ss = gc.open_by_key(get_sheet_id())
ws = ss.worksheet('🎯 비중조절신호')

updates = []

# Update PLTR (Row 12)
updates.append({'range': 'Z12', 'values': [['-']]})
updates.append({'range': 'AA12', 'values': [['-']]})
updates.append({'range': 'AB12', 'values': [['N/A (Kelly)']]})

# Update 현대해상 (Row 13)
updates.append({'range': 'Z13', 'values': [[0.06]]})
updates.append({'range': 'AA13', 'values': [[0.05]]})
updates.append({'range': 'AB13', 'values': [['=Z13/AA13']]})
updates.append({'range': 'O13', 'values': [['=MAX(0, MIN(0.05 * AB13, 0.15))']]})

ws.batch_update(updates, value_input_option='USER_ENTERED')
print("Successfully synced PLTR and 현대해상 to the new Z~AB structure.")
