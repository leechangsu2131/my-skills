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

print(f"Found {len(rules)} existing conditional format rules. Deleting them...")

requests = []
# Delete rules in reverse order to avoid index shifting
for i in range(len(rules)-1, -1, -1):
    requests.append({
        "deleteConditionalFormatRule": {
            "index": i,
            "sheetId": sheet_id
        }
    })

# Now add the 4 new clean rules
reqs_new = [
    # Rule 1: F~H (Target Price area) -> Grey out if Income
    {
        "addConditionalFormatRule": {
            "rule": {
                "ranges": [{"sheetId": sheet_id, "startRowIndex": 4, "endRowIndex": 100, "startColumnIndex": 5, "endColumnIndex": 8}],
                "booleanRule": {
                    "condition": {
                        "type": "CUSTOM_FORMULA",
                        "values": [{"userEnteredValue": '=$C5="인컴"'}]
                    },
                    "format": {"backgroundColor": {"red": 0.85, "green": 0.85, "blue": 0.85}, "textFormat": {"foregroundColor": {"red": 0.6, "green": 0.6, "blue": 0.6}}}
                }
            },
            "index": 0
        }
    },
    # Rule 2: I~N (Downside etc) -> Grey out if NOT Growth
    {
        "addConditionalFormatRule": {
            "rule": {
                "ranges": [{"sheetId": sheet_id, "startRowIndex": 4, "endRowIndex": 100, "startColumnIndex": 8, "endColumnIndex": 14}],
                "booleanRule": {
                    "condition": {
                        "type": "CUSTOM_FORMULA",
                        "values": [{"userEnteredValue": '=$C5<>"성장"'}]
                    },
                    "format": {"backgroundColor": {"red": 0.85, "green": 0.85, "blue": 0.85}, "textFormat": {"foregroundColor": {"red": 0.6, "green": 0.6, "blue": 0.6}}}
                }
            },
            "index": 1
        }
    },
    # Rule 3: Z~AA (Deprecated) -> Grey out ALWAYS
    {
        "addConditionalFormatRule": {
            "rule": {
                "ranges": [{"sheetId": sheet_id, "startRowIndex": 3, "endRowIndex": 100, "startColumnIndex": 25, "endColumnIndex": 27}],
                "booleanRule": {
                    "condition": {
                        "type": "CUSTOM_FORMULA",
                        "values": [{"userEnteredValue": '=TRUE'}]
                    },
                    "format": {"backgroundColor": {"red": 0.85, "green": 0.85, "blue": 0.85}, "textFormat": {"foregroundColor": {"red": 0.6, "green": 0.6, "blue": 0.6}}}
                }
            },
            "index": 2
        }
    },
    # Rule 4: AB~AC (Dividend) -> Grey out if NOT Income
    {
        "addConditionalFormatRule": {
            "rule": {
                "ranges": [{"sheetId": sheet_id, "startRowIndex": 4, "endRowIndex": 100, "startColumnIndex": 27, "endColumnIndex": 29}],
                "booleanRule": {
                    "condition": {
                        "type": "CUSTOM_FORMULA",
                        "values": [{"userEnteredValue": '=$C5<>"인컴"'}]
                    },
                    "format": {"backgroundColor": {"red": 0.85, "green": 0.85, "blue": 0.85}, "textFormat": {"foregroundColor": {"red": 0.6, "green": 0.6, "blue": 0.6}}}
                }
            },
            "index": 3
        }
    }
]

requests.extend(reqs_new)

if requests:
    ss.batch_update({"requests": requests})
    print("Successfully deleted old rules and applied 4 fresh clean rules.")
else:
    print("No rules to process.")

