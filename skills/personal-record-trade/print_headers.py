import sys
import json
from gsheet_auth import get_client, get_sheet_id

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

client = get_client()
doc = client.open_by_key(get_sheet_id())
ws = doc.worksheet("🎯 비중조절신호")

headers = ws.row_values(4)
row_5 = ws.row_values(5)

print(json.dumps({"headers": headers, "row_5": row_5}, ensure_ascii=False))
