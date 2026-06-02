import gspread
import sys

sys.path.append(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\personal-record-trade")
from gsheet_auth import get_client, get_sheet_id

gc = get_client()
ss = gc.open_by_key(get_sheet_id())
ws = ss.worksheet('🎯 비중조절신호')
sheet_id = ws.id

# Fetch current spreadsheet metadata
meta = ss.fetch_sheet_metadata()
sheets = meta.get('sheets', [])
sheet_meta = next(s for s in sheets if s['properties']['sheetId'] == sheet_id)
rules = sheet_meta.get('conditionalFormats', [])

requests = []
# Delete ALL conditional formatting rules
for i in range(len(rules)-1, -1, -1):
    requests.append({
        "deleteConditionalFormatRule": {
            "index": i,
            "sheetId": sheet_id
        }
    })

if requests:
    ss.batch_update({"requests": requests})
    print("Successfully deleted ALL conditional formatting rules.")
else:
    print("No rules to delete.")
