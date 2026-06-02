import gspread
import sys
import json

sys.path.append(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\personal-record-trade")
from gsheet_auth import get_client, get_sheet_id

gc = get_client()
ss = gc.open_by_key(get_sheet_id())
ws = ss.worksheet('🎯 비중조절신호')
sheet_id = ws.id

res = ss.client.request('get', f'https://sheets.googleapis.com/v4/spreadsheets/{ss.id}?ranges=🎯 비중조절신호!F5:N15&includeGridData=true')
grid_data = res.json()['sheets'][0]['data'][0].get('rowData', [])

print("--- UserEntered vs Effective Colors ---")
for i, row in enumerate(grid_data):
    row_idx = 5 + i
    colors = []
    if 'values' in row:
        for col_idx, cell in enumerate(row['values']):
            col_letter = chr(ord('F') + col_idx)
            
            # Base color (user manually painted)
            user_format = cell.get('userEnteredFormat', {})
            user_bg = user_format.get('backgroundColor', {})
            is_user_grey = (user_bg.get('red', 1.0) < 0.9 and user_bg.get('green', 1.0) < 0.9)
            user_str = "GREY" if is_user_grey else "WHITE"
            
            # Effective color (what you see on screen)
            eff_format = cell.get('effectiveFormat', {})
            eff_bg = eff_format.get('backgroundColor', {})
            is_eff_grey = (eff_bg.get('red', 1.0) < 0.9 and eff_bg.get('green', 1.0) < 0.9)
            eff_str = "GREY" if is_eff_grey else "WHITE"
            
            # Only print if they differ from WHITE/WHITE or if it's row 5 or 12
            if is_user_grey or is_eff_grey or row_idx in [5, 12]:
                colors.append(f"{col_letter}:(Base:{user_str}, Eff:{eff_str})")
    
    if colors:
        print(f"Row {row_idx}: " + ", ".join(colors))
