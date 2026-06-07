import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, 'reconfigure'):
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

from gsheet_auth import get_client, get_sheet_id

def main():
    client = get_client()
    doc = client.open_by_key(get_sheet_id())
    ws = doc.worksheet("🎯 비중조절신호")
    
    cell = ws.acell('AE8', value_render_option='FORMULA')
    print(f"Formula in AE8: {cell.value}")
    
    cell_val = ws.acell('AE8')
    print(f"Value in AE8: {cell_val.value}")
    
    print(f"Row 8: {ws.row_values(8)}")
    
    # Let's get the headers in row 7 (usually the column names)
    print(f"Row 7: {ws.row_values(7)}")
    
    # Also get the target cell K3 to see the KOSPI market cap
    k3 = ws.acell('K3').value
    print(f"Value in K3 (KOSPI Market Cap): {k3}")

if __name__ == "__main__":
    main()
