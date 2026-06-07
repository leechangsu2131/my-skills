import sys
from gsheet_auth import get_client, get_sheet_id

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

client = get_client()
doc = client.open_by_key(get_sheet_id())
ws = doc.worksheet("🎯 비중조절신호")

ws.update_acell('AE35', '=GOOGLEFINANCE("000660", "name")')
v1 = ws.acell('AE35').value
print(f"000660 Name: {v1}")
