import sys
from gsheet_auth import get_client, get_sheet_id

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

doc = get_client().open_by_key(get_sheet_id())
for ws in doc.worksheets():
    print(ws.title)
