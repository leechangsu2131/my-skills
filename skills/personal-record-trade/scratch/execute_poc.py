import gspread
import sys

sys.path.append(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\personal-record-trade")
from gsheet_auth import get_client, get_sheet_id

gc = get_client()
ss = gc.open_by_key(get_sheet_id())
ws = ss.worksheet('🎯 비중조절신호')

records = ws.get_all_values()

# 1. Set headers in Y4, Z4, AA4
updates = [
    {'range': 'Y4', 'values': [['지표1(PER/배당)']]},
    {'range': 'Z4', 'values': [['지표2(Target/기타)']]},
    {'range': 'AA4', 'values': [['퀄리티스코어']]}
]

# Find targets
goog_row = None
pltr_row = None
insur_row = None

for i, r in enumerate(records):
    ticker = r[0] # Ticker is in column A
    row_idx = i + 1
    if 'GOOG' in ticker:
        goog_row = row_idx
    elif 'PLTR' in ticker:
        pltr_row = row_idx
    elif '001450' in ticker or '현대해상' in str(r):
        insur_row = row_idx

# 2. Update GOOG (Core)
if goog_row:
    # Y = Current PE (via googlefinance)
    # Z = Target PE (e.g. 25 as historical average)
    # AA = Target PE / Current PE
    # O (Model Weight) = (Core Budget / Count of Core) * Score (max 15%)
    # Let's assume Target Core budget is in AB4 (=45%), but to avoid complex formulas, we'll use a fixed base of 5% per core stock.
    # Base weight = 0.05
    updates.append({'range': f'Y{goog_row}', 'values': [[f'=GOOGLEFINANCE("GOOG", "pe")']]})
    updates.append({'range': f'Z{goog_row}', 'values': [[25]]}) # Target PE
    updates.append({'range': f'AA{goog_row}', 'values': [[f'=MAX(0.5, MIN(1.5, Z{goog_row}/Y{goog_row}))']]})
    updates.append({'range': f'O{goog_row}', 'values': [[f'=MAX(0, MIN(0.05 * AA{goog_row}, 0.15))']]})

# 3. Update 현대해상 (Income)
if insur_row:
    # Y = Current Div Yield (manual 6%)
    # Z = Target Div Yield (5%)
    # AA = Current / Target
    # Base weight = 0.05
    updates.append({'range': f'Y{insur_row}', 'values': [[0.06]]})
    updates.append({'range': f'Z{insur_row}', 'values': [[0.05]]})
    updates.append({'range': f'AA{insur_row}', 'values': [[f'=Y{insur_row}/Z{insur_row}']]})
    updates.append({'range': f'O{insur_row}', 'values': [[f'=MAX(0, MIN(0.05 * AA{insur_row}, 0.15))']]})

# 4. Update PLTR (Growth)
if pltr_row:
    # AA = N/A
    # O = Kelly (already there, but re-assert it to be safe)
    o_formula = f'=IF(A{pltr_row}="","", MAX(0, MIN(0.2 * ( (D{pltr_row} / MAX((E{pltr_row}-I{pltr_row})/E{pltr_row}, 0.001)) - ((1-D{pltr_row}) / MAX((H{pltr_row}-E{pltr_row})/E{pltr_row}, 0.001)) ), 0.15)))'
    updates.append({'range': f'Y{pltr_row}', 'values': [['-']]})
    updates.append({'range': f'Z{pltr_row}', 'values': [['-']]})
    updates.append({'range': f'AA{pltr_row}', 'values': [['N/A (Kelly)']]} )
    updates.append({'range': f'O{pltr_row}', 'values': [[o_formula]]})

ws.batch_update(updates, value_input_option='USER_ENTERED')
print("PoC updates completed successfully.")
