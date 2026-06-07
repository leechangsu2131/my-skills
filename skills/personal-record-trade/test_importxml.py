import sys
from gsheet_auth import get_client, get_sheet_id

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

client = get_client()
doc = client.open_by_key(get_sheet_id())
ws = doc.worksheet("🎯 비중조절신호")

ws.update_acell('AE32', '=IMPORTXML("https://finance.naver.com/item/main.naver?code=000660", "//*[@id=\'_market_sum\']")')

v1 = ws.acell('AE32').value

print(f"Hynix IMPORTXML: {v1}")
