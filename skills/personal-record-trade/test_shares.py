import sys
from gsheet_auth import get_client, get_sheet_id

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

client = get_client()
doc = client.open_by_key(get_sheet_id())
ws = doc.worksheet("🎯 비중조절신호")

ws.update_acell('AE32', '=GOOGLEFINANCE("000660", "shares")')
ws.update_acell('AE33', '=GOOGLEFINANCE("005930", "shares")')

v1 = ws.acell('AE32').value
v2 = ws.acell('AE33').value

print(f"Hynix shares: {v1}")
print(f"Samsung shares: {v2}")
