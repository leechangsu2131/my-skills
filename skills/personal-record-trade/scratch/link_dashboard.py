import gspread
import sys

sys.path.append(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\personal-record-trade")
from gsheet_auth import get_client, get_sheet_id

gc = get_client()
ss = gc.open_by_key(get_sheet_id())

# 1. Update 🎯 비중조절신호 Target Budgets to link to 🏠 대시보드
ws_weight = ss.worksheet('🎯 비중조절신호')
updates_weight = [
    {'range': 'AB3', 'values': [["='🏠 대시보드'!J10"]]},
    {'range': 'AB4', 'values': [["='🏠 대시보드'!J11"]]},
    {'range': 'AB5', 'values': [["='🏠 대시보드'!J12"]]}
]
ws_weight.batch_update(updates_weight, value_input_option='USER_ENTERED')
print("Linked 🎯 비중조절신호 to 🏠 대시보드 target budgets.")

# 2. Update 🏠 대시보드 매매신호 counters
ws_dash = ss.worksheet('🏠 대시보드')
updates_dash = [
    {'range': 'F6', 'values': [["=COUNTIF('🎯 비중조절신호'!R:R, \"*비중확대*\")"]]},
    {'range': 'G6', 'values': [["=COUNTIF('🎯 비중조절신호'!R:R, \"*비중축소*\")"]]}
]
ws_dash.batch_update(updates_dash, value_input_option='USER_ENTERED')
print("Updated 🏠 대시보드 trade signal counters to match new R column text.")
