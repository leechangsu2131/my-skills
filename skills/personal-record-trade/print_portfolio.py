import sys
import json
from gsheet_auth import get_client, get_sheet_id

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

client = get_client()
doc = client.open_by_key(get_sheet_id())
ws = doc.worksheet("📊 포트폴리오")

data = ws.get_all_values()
for row in data[:20]:
    print(json.dumps(row[:15], ensure_ascii=False))
