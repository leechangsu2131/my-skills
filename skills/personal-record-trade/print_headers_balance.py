import sys
import json
from gsheet_auth import get_client, get_sheet_id

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

client = get_client()
doc = client.open_by_key(get_sheet_id())
ws = doc.worksheet("📅 특정일잔고")

print(json.dumps(ws.row_values(1)[:20], ensure_ascii=False))
print(json.dumps(ws.row_values(2)[:20], ensure_ascii=False))
print(json.dumps(ws.row_values(3)[:20], ensure_ascii=False))
