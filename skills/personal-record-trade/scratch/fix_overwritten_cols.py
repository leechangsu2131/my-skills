import gspread
import sys

sys.path.append(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\personal-record-trade")
from gsheet_auth import get_client, get_sheet_id

gc = get_client()
ss = gc.open_by_key(get_sheet_id())
ws = ss.worksheet('🎯 비중조절신호')

# Expand grid to 33 columns (AG)
if ws.col_count < 33:
    ws.resize(rows=ws.row_count, cols=33)

updates = []

# 1. Restore Y column (Risk-Adjusted Return formula)
updates.append({'range': 'Y4', 'values': [['위험대비기대수익']]}) 
updates.append({'range': 'Y5', 'values': [['=IFERROR(M5 / ABS((I5-E5)/E5), 0)']]})
updates.append({'range': 'Y12', 'values': [['=IFERROR(M12 / ABS((I12-E12)/E12), 0)']]})
updates.append({'range': 'Y13', 'values': [['=IFERROR(M13 / ABS((I13-E13)/E13), 0)']]})

# 2. Restore Z column (Clear my overwrites)
updates.append({'range': 'Z4', 'values': [['']]})
updates.append({'range': 'Z5', 'values': [['']]})
updates.append({'range': 'Z12', 'values': [['']]})
updates.append({'range': 'Z13', 'values': [['']]})

# 3. Restore AA column (Dashboard parts I broke)
updates.append({'range': 'AA4', 'values': [['코어']]})
updates.append({'range': 'AA5', 'values': [['인컴']]})
updates.append({'range': 'AA12', 'values': [['']]})
updates.append({'range': 'AA13', 'values': [['']]})

# 4. Re-apply PoC to AE, AF, AG
updates.append({'range': 'AE4', 'values': [['지표1(PER/배당)']]})
updates.append({'range': 'AF4', 'values': [['지표2(Target/기타)']]})
updates.append({'range': 'AG4', 'values': [['퀄리티스코어']]})

# GOOG (Row 5)
goog_row = 5
updates.append({'range': f'AE{goog_row}', 'values': [[f'=GOOGLEFINANCE("GOOG", "pe")']]})
updates.append({'range': f'AF{goog_row}', 'values': [[25]]})
updates.append({'range': f'AG{goog_row}', 'values': [[f'=MAX(0.5, MIN(1.5, AF{goog_row}/AE{goog_row}))']]})
updates.append({'range': f'O{goog_row}', 'values': [[f'=MAX(0, MIN(0.05 * AG{goog_row}, 0.15))']]})

# PLTR (Row 12)
pltr_row = 12
updates.append({'range': f'AE{pltr_row}', 'values': [['-']]})
updates.append({'range': f'AF{pltr_row}', 'values': [['-']]})
updates.append({'range': f'AG{pltr_row}', 'values': [['N/A (Kelly)']]})
o_formula_pltr = f'=IF(A{pltr_row}="","", MAX(0, MIN(0.2 * ( (D{pltr_row} / MAX((E{pltr_row}-I{pltr_row})/E{pltr_row}, 0.001)) - ((1-D{pltr_row}) / MAX((H{pltr_row}-E{pltr_row})/E{pltr_row}, 0.001)) ), 0.15)))'
updates.append({'range': f'O{pltr_row}', 'values': [[o_formula_pltr]]})

# 현대해상 (Row 13)
insur_row = 13
updates.append({'range': f'AE{insur_row}', 'values': [[0.06]]})
updates.append({'range': f'AF{insur_row}', 'values': [[0.05]]})
updates.append({'range': f'AG{insur_row}', 'values': [[f'=AE{insur_row}/AF{insur_row}']]})
updates.append({'range': f'O{insur_row}', 'values': [[f'=MAX(0, MIN(0.05 * AG{insur_row}, 0.15))']]})

ws.batch_update(updates, value_input_option='USER_ENTERED')
print("Successfully resized columns, restored Y/Z/AA, and moved PoC to AE-AG.")
