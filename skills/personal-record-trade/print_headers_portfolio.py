import sys
import json
from gsheet_auth import get_client, get_sheet_id

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

client = get_client()
doc = client.open_by_key(get_sheet_id())
ws = doc.worksheet("📊 포트폴리오")

headers = ws.row_values(1)
row_2 = ws.row_values(2)

print(json.dumps({"headers": headers, "row_2": row_2}, ensure_ascii=False))
