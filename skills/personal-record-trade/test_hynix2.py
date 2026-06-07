import sys
from gsheet_auth import get_client, get_sheet_id

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

client = get_client()
doc = client.open_by_key(get_sheet_id())
ws = doc.worksheet("🎯 비중조절신호")

cell_val = ws.acell('AE27').value
cell_form = ws.acell('AE27', value_render_option='FORMULA').value
ticker = ws.acell('A27').value
k3 = ws.acell('K3').value

print(f"Hynix AE27 Value: {cell_val}")
print(f"Hynix AE27 Formula: {cell_form}")
print(f"Hynix Ticker (A27): {ticker}")
print(f"K3 (KOSPI Market Cap): {k3}")
