import gspread
import sys

sys.path.append(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\personal-record-trade")
from gsheet_auth import get_client, get_sheet_id

gc = get_client()
ss = gc.open_by_key(get_sheet_id())
ws = ss.worksheet('🎯 비중조절신호')
sheet_id = ws.id

# 1. Update Formulas for AD and O
updates = []
for row_idx in range(5, 101):
    r = str(row_idx)
    
    # Z (Current PER) auto-fill formula for ease (optional, but let's just make sure AD and O are perfectly unified)
    # AD (Quality Score)
    ad_formula = f'=IF(C{r}="코어", IFERROR(MAX(0.5, MIN(1.5, AA{r}/Z{r})), 1), IF(C{r}="인컴", IFERROR(AB{r}/AC{r}, 1), 1))'
    updates.append({'range': f'AD{r}', 'values': [[ad_formula]]})
    
    # O (Model Weight)
    kelly_part = f'IFERROR(MAX(0, MIN(0.2 * ( (D{r} / MAX((E{r}-I{r})/E{r}, 0.001)) - ((1-D{r}) / MAX((H{r}-E{r})/E{r}, 0.001)) ), 0.15)), 0)'
    val_part = f'IFERROR(MAX(0, MIN(0.05 * AD{r}, 0.15)), 0)'
    o_formula = f'=IF(C{r}="성장", {kelly_part}, IF(OR(C{r}="코어", C{r}="인컴"), {val_part}, ""))'
    updates.append({'range': f'O{r}', 'values': [[o_formula]]})

ws.batch_update(updates, value_input_option='USER_ENTERED')
print("Successfully rolled out O and AD formulas to rows 5-100.")

# 2. Apply Conditional Formatting
# First, clear existing conditional formatting if any, or just add new rules.
# It's safer to just add the rules at index 0.
reqs = [
    {
        "addConditionalFormatRule": {
            "rule": {
                "ranges": [{"sheetId": sheet_id, "startRowIndex": 4, "endRowIndex": 100, "startColumnIndex": 5, "endColumnIndex": 14}], # F(5) to N(13) -> Wait, N is 13. F is 5.
                "booleanRule": {
                    "condition": {
                        "type": "CUSTOM_FORMULA",
                        "values": [{"userEnteredValue": '=OR($C5="코어", $C5="인컴")'}]
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
    {
        "addConditionalFormatRule": {
            "rule": {
                "ranges": [{"sheetId": sheet_id, "startRowIndex": 4, "endRowIndex": 100, "startColumnIndex": 25, "endColumnIndex": 29}], # Z(25) to AC(28)
                "booleanRule": {
                    "condition": {
                        "type": "CUSTOM_FORMULA",
                        "values": [{"userEnteredValue": '=$C5="성장"'}]
                    },
                    "format": {
                        "backgroundColor": {"red": 0.85, "green": 0.85, "blue": 0.85},
                        "textFormat": {"foregroundColor": {"red": 0.6, "green": 0.6, "blue": 0.6}}
                    }
                }
            },
            "index": 1
        }
    }
]

res = ss.batch_update({"requests": reqs})
print("Successfully applied conditional formatting rules.")
