import gspread
import sys

sys.path.append(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\personal-record-trade")
from gsheet_auth import get_client, get_sheet_id

gc = get_client()
ss = gc.open_by_key(get_sheet_id())

# 1. Update buckets in Portfolio
ws_portfolio = ss.worksheet('📊 포트폴리오')
records = ws_portfolio.get_all_values()

updates_portfolio = []
for i, r in enumerate(records):
    ticker = r[4] or r[2]  # ticker column
    row_idx = i + 1
    
    # User requested: NFLX, ORCL, SK하이닉스(000660) to Core
    if 'NFLX' in ticker or 'ORCL' in ticker or '000660' in ticker:
        if r[6] != '코어':
            updates_portfolio.append({'range': f'G{row_idx}', 'values': [['코어']]})

if updates_portfolio:
    ws_portfolio.batch_update(updates_portfolio, value_input_option='USER_ENTERED')
    print("Updated bucket classifications in Portfolio: NFLX, ORCL, SK하이닉스 -> 코어")

# 2. Update Target Budgets in 🎯 비중조절신호
ws_weight = ss.worksheet('🎯 비중조절신호')
# AA3: 성장, AA4: 코어, AA5: 인컴
# AB3: Growth Target (0.30)
# AB4: Core Target (0.45)
# AB5: Income Target (0.15)
updates_weight = [
    {'range': 'AB3', 'values': [[0.30]]},
    {'range': 'AB4', 'values': [[0.45]]},
    {'range': 'AB5', 'values': [[0.15]]}
]
ws_weight.batch_update(updates_weight, value_input_option='USER_ENTERED')
print("Updated target budgets in 🎯 비중조절신호: 성장 30%, 코어 45%, 인컴 15%")
