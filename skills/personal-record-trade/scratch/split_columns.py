import gspread
import sys

sys.path.append(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\personal-record-trade")
from gsheet_auth import get_client, get_sheet_id

gc = get_client()
ss = gc.open_by_key(get_sheet_id())
ws = ss.worksheet('🎯 비중조절신호')

updates = []

# Update Headers in Z~AD
updates.append({'range': 'Z4', 'values': [['현재PER (코어)']]} )
updates.append({'range': 'AA4', 'values': [['타겟PER (코어)']]} )
updates.append({'range': 'AB4', 'values': [['현재배당 (인컴)']]} )
updates.append({'range': 'AC4', 'values': [['타겟배당 (인컴)']]} )
updates.append({'range': 'AD4', 'values': [['퀄리티스코어']]} )

# Clear existing PoC data in Z, AA, AB, AC, AD
for row in [5, 12, 13]:
    updates.append({'range': f'Z{row}:AD{row}', 'values': [['', '', '', '', '']]})

# 1. GOOG (Core) - Row 5
goog_row = 5
updates.append({'range': f'Z{goog_row}', 'values': [[f'=GOOGLEFINANCE("GOOG", "pe")']]})
updates.append({'range': f'AA{goog_row}', 'values': [[25]]})
# Score = Target PER / Current PER
updates.append({'range': f'AD{goog_row}', 'values': [[f'=IFERROR(MAX(0.5, MIN(1.5, AA{goog_row}/Z{goog_row})), 1)']]})
updates.append({'range': f'O{goog_row}', 'values': [[f'=MAX(0, MIN(0.05 * AD{goog_row}, 0.15))']]})

# 2. PLTR (Growth) - Row 12
pltr_row = 12
updates.append({'range': f'Z{pltr_row}', 'values': [['-']]})
updates.append({'range': f'AA{pltr_row}', 'values': [['-']]})
updates.append({'range': f'AB{pltr_row}', 'values': [['-']]})
updates.append({'range': f'AC{pltr_row}', 'values': [['-']]})
updates.append({'range': f'AD{pltr_row}', 'values': [['(켈리 기반)']]} )
# O remains Kelly

# 3. 현대해상 (Income) - Row 13
insur_row = 13
updates.append({'range': f'AB{insur_row}', 'values': [[0.06]]})
updates.append({'range': f'AC{insur_row}', 'values': [[0.05]]})
# Score = Current Div / Target Div
updates.append({'range': f'AD{insur_row}', 'values': [[f'=IFERROR(AB{insur_row}/AC{insur_row}, 1)']]})
updates.append({'range': f'O{insur_row}', 'values': [[f'=MAX(0, MIN(0.05 * AD{insur_row}, 0.15))']]})

ws.batch_update(updates, value_input_option='USER_ENTERED')
print("Separated PER and Dividend columns for clarity.")
