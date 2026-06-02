import gspread
import sys

sys.path.append(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\personal-record-trade")
from gsheet_auth import get_client, get_sheet_id

gc = get_client()
ss = gc.open_by_key(get_sheet_id())
ws = ss.worksheet('🎯 비중조절신호')
sheet_id = ws.id

res = ss.client.request('get', f'https://sheets.googleapis.com/v4/spreadsheets/{ss.id}?ranges=🎯 비중조절신호!Z5:AD15&includeGridData=true')
grid_data = res.json()['sheets'][0]['data'][0]['rowData']

print("--- Effective Background Colors (Z~AD) ---")
for i, row in enumerate(grid_data):
    row_idx = 5 + i
    colors = []
    if 'values' in row:
        for col_idx, cell in enumerate(row['values']):
            col_letter = chr(ord('Z') + col_idx) if col_idx <= 0 else "A" + chr(ord('A') + col_idx - 1)
            eff_format = cell.get('effectiveFormat', {})
            bg = eff_format.get('backgroundColor', {})
            is_grey = (bg.get('red', 1.0) < 0.9 and bg.get('green', 1.0) < 0.9)
            color_str = "GREY" if is_grey else "WHITE"
            colors.append(f"{col_letter}:{color_str}")
    print(f"Row {row_idx}: " + ", ".join(colors))
