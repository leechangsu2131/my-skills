import sys
import json
from gsheet_auth import get_client, get_sheet_id

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

client = get_client()
doc = client.open_by_key(get_sheet_id())
ws = doc.worksheet("🔬 기업분석")

print("Row 3:", json.dumps(ws.row_values(3), ensure_ascii=False))
print("Row 4:", json.dumps(ws.row_values(4), ensure_ascii=False))
