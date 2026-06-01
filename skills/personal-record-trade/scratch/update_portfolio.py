import gspread
import sys

sys.path.append(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\personal-record-trade")
from gsheet_auth import get_client, get_sheet_id

gc = get_client()
ss = gc.open_by_key(get_sheet_id())
ws = ss.worksheet('📊 포트폴리오')

records = ws.get_all_values()

# Updates required:
# TIGER S&P500 (360750): -782 shares, proceeds = +22,341,740
# PLUS Tech TOP10 (461900): -1166 shares, proceeds = +29,650,214
# SOL AI Software (481180): -615 shares, proceeds = +10,399,650
# Total KRW Cash to add: 62,391,604

# Cell indices to update
updates = []

for i, row in enumerate(records):
    ticker = row[2]  # Column C (index 2)
    
    if ticker == '360750':
        current_qty = int(row[7].replace(',', ''))
        new_qty = current_qty - 782
        updates.append({'range': f'H{i+1}', 'values': [[new_qty]]})
        print(f"TIGER S&P500 (Row {i+1}): {current_qty} -> {new_qty}")
        
    elif ticker == '461900':
        current_qty = int(row[7].replace(',', ''))
        new_qty = current_qty - 1166
        updates.append({'range': f'H{i+1}', 'values': [[new_qty]]})
        print(f"PLUS Tech TOP10 (Row {i+1}): {current_qty} -> {new_qty}")
        
    elif ticker == '481180':
        current_qty = int(row[7].replace(',', ''))
        new_qty = current_qty - 615
        updates.append({'range': f'H{i+1}', 'values': [[new_qty]]})
        print(f"SOL AI Software (Row {i+1}): {current_qty} -> {new_qty}")
        
    elif ticker == '원화':
        current_cash = int(row[7].replace(',', ''))
        new_cash = current_cash + 62391604
        updates.append({'range': f'H{i+1}', 'values': [[new_cash]]})
        # Note: formatting will remain, or we can format as string with commas
        updates[-1]['values'] = [[f"{new_cash:,}"]]
        print(f"KRW Cash (Row {i+1}): {current_cash:,} -> {new_cash:,}")

# Execute updates
if updates:
    ws.batch_update(updates, value_input_option='USER_ENTERED')
    print("Portfolio quantities updated successfully!")
else:
    print("Could not find the target rows.")
