import sys
import os
from pathlib import Path

# Windows cp949 인코딩 오류 방지
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from gsheet_auth import get_client

def inspect_sheet():
    sheet_id = "12csrOj-6xgW45JSjbh8O9okxmA34eaatszvio6hQlmc"
    target_gid = 1127641143
    
    print(f"Connecting to Google Sheet ID: {sheet_id} ...")
    client = get_client()
    doc = client.open_by_key(sheet_id)
    
    print("Worksheets in this document:")
    target_ws = None
    for ws in doc.worksheets():
        ws_id = ws.id
        print(f" - Title: '{ws.title}', ID (GID): {ws_id}")
        if ws_id == target_gid:
            target_ws = ws
            
    if not target_ws:
        print(f"Could not find worksheet with GID {target_gid}. Using the first sheet instead.")
        target_ws = doc.get_worksheet(0)
        
        print(f"\nReading raw rows from '{target_ws.title}'...")
    row4 = target_ws.row_values(4)
    print(f"Row 4 values (len={len(row4)}): {row4}")
    
    rows5_7 = target_ws.get_values("A5:W7")
    print("\nRows 5 to 7 raw values:")
    for idx, row in enumerate(rows5_7):
        print(f" Row {idx+5}: {row}")
            
if __name__ == "__main__":
    inspect_sheet()
