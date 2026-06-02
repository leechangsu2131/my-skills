import gspread
import sys

sys.path.append(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\personal-record-trade")
from gsheet_auth import get_client, get_sheet_id

gc = get_client()
ss = gc.open_by_key(get_sheet_id())
ws = ss.worksheet('🎯 비중조절신호')
sheet_id = ws.id

# 1. Clear Z and AA (Columns 25 and 26, 0-indexed)
updates = []
updates.append({'range': 'Z4:AA100', 'values': [['', ''] for _ in range(97)]})

# 2. Update AD (Quality Score) formula
for row_idx in range(5, 101):
    r = str(row_idx)
    ad_formula = f'=IF(C{r}="코어", IFERROR(MAX(0.5, MIN(1.5, H{r}/E{r})), 1), IF(C{r}="인컴", IFERROR(AB{r}/AC{r}, 1), 1))'
    updates.append({'range': f'AD{r}', 'values': [[ad_formula]]})

ws.batch_update(updates, value_input_option='USER_ENTERED')
print("Successfully cleared Z, AA and updated AD formulas.")

# 3. Conditional Formatting Rules
reqs = [
    # Rule 1: F~H (Value Model to Target Price) -> Grey out if Income
    {
        "addConditionalFormatRule": {
            "rule": {
                "ranges": [{"sheetId": sheet_id, "startRowIndex": 4, "endRowIndex": 100, "startColumnIndex": 5, "endColumnIndex": 8}], # F(5), G(6), H(7)
                "booleanRule": {
                    "condition": {
                        "type": "CUSTOM_FORMULA",
                        "values": [{"userEnteredValue": '=$C5="인컴"'}]
                    },
                    "format": {
                        "backgroundColor": {"red": 0.85, "green": 0.85, "blue": 0.85},
                        "textFormat": {"foregroundColor": {"red": 0.6, "green": 0.6, "blue": 0.6}}
                    }
                }
            },
            "index": 0
        }
    },
    # Rule 2: I~N (Downside to Risk Limit) -> Grey out if NOT Growth
    {
        "addConditionalFormatRule": {
            "rule": {
                "ranges": [{"sheetId": sheet_id, "startRowIndex": 4, "endRowIndex": 100, "startColumnIndex": 8, "endColumnIndex": 14}], # I(8) to N(13)
                "booleanRule": {
                    "condition": {
                        "type": "CUSTOM_FORMULA",
                        "values": [{"userEnteredValue": '=$C5<>"성장"'}]
                    },
                    "format": {
                        "backgroundColor": {"red": 0.85, "green": 0.85, "blue": 0.85},
                        "textFormat": {"foregroundColor": {"red": 0.6, "green": 0.6, "blue": 0.6}}
                    }
                }
            },
            "index": 1
        }
    },
    # Rule 3: Z~AA (Deprecated PER columns) -> Grey out ALWAYS
    {
        "addConditionalFormatRule": {
            "rule": {
                "ranges": [{"sheetId": sheet_id, "startRowIndex": 3, "endRowIndex": 100, "startColumnIndex": 25, "endColumnIndex": 27}], # Z(25), AA(26)
                "booleanRule": {
                    "condition": {
                        "type": "CUSTOM_FORMULA",
                        "values": [{"userEnteredValue": '=TRUE'}]
                    },
                    "format": {
                        "backgroundColor": {"red": 0.85, "green": 0.85, "blue": 0.85},
                        "textFormat": {"foregroundColor": {"red": 0.6, "green": 0.6, "blue": 0.6}}
                    }
                }
            },
            "index": 2
        }
    },
    # Rule 4: AB~AC (Dividend columns) -> Grey out if NOT Income
    {
        "addConditionalFormatRule": {
            "rule": {
                "ranges": [{"sheetId": sheet_id, "startRowIndex": 4, "endRowIndex": 100, "startColumnIndex": 27, "endColumnIndex": 29}], # AB(27), AC(28)
                "booleanRule": {
                    "condition": {
                        "type": "CUSTOM_FORMULA",
                        "values": [{"userEnteredValue": '=$C5<>"인컴"'}]
                    },
                    "format": {
                        "backgroundColor": {"red": 0.85, "green": 0.85, "blue": 0.85},
                        "textFormat": {"foregroundColor": {"red": 0.6, "green": 0.6, "blue": 0.6}}
                    }
                }
            },
            "index": 3
        }
    }
]

res = ss.batch_update({"requests": reqs})
print("Successfully applied precise conditional formatting rules.")
