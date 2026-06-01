import gspread
import sys
import re

sys.path.append(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\personal-record-trade")
from gsheet_auth import get_client, get_sheet_id

gc = get_client()
ss = gc.open_by_key(get_sheet_id())
ws = ss.worksheet('🎯 비중조절신호')

records = ws.get_all_values(value_render_option='FORMULA')

# Find first empty row
insert_row = len(records) + 1
for i, row in enumerate(records):
    if i > 3 and (len(row) == 0 or str(row[0]).strip() == ''):
        insert_row = i + 1
        break

# Row 5 (index 4) has all the correct formulas (GOOG)
template_row = records[4]

new_row = []
for cell in template_row:
    cell_str = str(cell)
    # Replace references like A5, B5 to A{insert_row}, B{insert_row}
    # Be careful not to replace fixed references like $C$5 (wait, $C$5 shouldn't be replaced, but actually it's fine if it's C5, but $C$5 is usually absolute).
    # Regex: replace A5 to Z5 only if it's a cell reference.
    # To be safe, we just replace all A5, B5 etc. with A{insert_row}
    for col in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        # Replace non-absolute references (e.g. A5)
        # We'll use regex to ensure it's not part of another word or number
        cell_str = re.sub(rf"(?<!\$)\b{col}5\b", f"{col}{insert_row}", cell_str)
        # Note: we don't replace $A$5 or $C$5 because of the negative lookbehind for $.
        # Wait, if it's $A5? In google sheets, $A5 is absolute col, relative row. It should be replaced.
        cell_str = re.sub(rf"\${col}5\b", f"${col}{insert_row}", cell_str)
    new_row.append(cell_str)

# Now, customize the hardcoded columns for Hanmi Semiconductor (042700)
# A: Ticker
new_row[0] = "042700"
# D: Conviction
new_row[3] = 0.5
# F: Model
new_row[5] = "직접입력"
# G: Target price input
new_row[6] = 350000
# I: Downside price
new_row[8] = 250000
# K: Annual return target
new_row[10] = 0.10
# O: Target model weight
new_row[14] = 0.05
# R: Trade signal (Wait, R is index 17)
new_row[17] = "대기"

ws.update(f"A{insert_row}:Y{insert_row}", [new_row], value_input_option='USER_ENTERED')
print(f"Added Hanmi Semiconductor to 🎯 비중조절신호 at row {insert_row}")
