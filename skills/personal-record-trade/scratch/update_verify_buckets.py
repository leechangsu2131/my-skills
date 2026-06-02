import gspread
import sys

sys.path.append(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\personal-record-trade")
from gsheet_auth import get_client, get_sheet_id

gc = get_client()
ss = gc.open_by_key(get_sheet_id())

targets = ['NFLX', 'ORCL', '000660', 'SK Hynix', 'Netflix', 'Oracle']

# 1. 포트폴리오 탭
ws_port = ss.worksheet('📊 포트폴리오')
records_port = ws_port.get_all_values()
updates_port = []
print("--- 📊 포트폴리오 탭 확인 ---")
for i, r in enumerate(records_port):
    row_text = str(r)
    if any(t in row_text for t in targets):
        if r[6] != '코어':
            updates_port.append({'range': f'G{i+1}', 'values': [['코어']]})
            print(f"Row {i+1}: {r[3] or r[2]} - '코어'로 변경 예약 (기존: {r[6]})")
        else:
            print(f"Row {i+1}: {r[3] or r[2]} - 이미 '코어'임")

if updates_port:
    ws_port.batch_update(updates_port, value_input_option='USER_ENTERED')
    print("포트폴리오 업데이트 완료!\n")
else:
    print("포트폴리오 업데이트할 내용 없음.\n")

# 2. 비중조절신호 탭
ws_weight = ss.worksheet('🎯 비중조절신호')
records_weight = ws_weight.get_all_values()
updates_weight = []
print("--- 🎯 비중조절신호 탭 확인 ---")
for i, r in enumerate(records_weight):
    if i < 4: continue # Skip headers
    row_text = str(r)
    if any(t in row_text for t in targets):
        if r[2] != '코어':
            updates_weight.append({'range': f'C{i+1}', 'values': [['코어']]})
            print(f"Row {i+1}: {r[1] or r[0]} - '코어'로 변경 예약 (기존: {r[2]})")
        else:
            print(f"Row {i+1}: {r[1] or r[0]} - 이미 '코어'임")

if updates_weight:
    ws_weight.batch_update(updates_weight, value_input_option='USER_ENTERED')
    print("비중조절신호 업데이트 완료!\n")
else:
    print("비중조절신호 업데이트할 내용 없음.\n")

# 3. 더블체크 (Verification)
print("--- ✅ 최종 검증 (더블체크) ---")
records_port_new = ws_port.get_all_values()
records_weight_new = ws_weight.get_all_values()

for i, r in enumerate(records_port_new):
    if any(t in str(r) for t in targets):
        print(f"포트폴리오 Row {i+1}: {r[3] or r[2]} -> 버킷: {r[6]}")

for i, r in enumerate(records_weight_new):
    if any(t in str(r) for t in targets):
        print(f"비중조절신호 Row {i+1}: {r[1] or r[0]} -> 버킷: {r[2]}")

