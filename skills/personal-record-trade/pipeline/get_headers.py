import sys
from pathlib import Path

# Windows cp949 인코딩 오류 방지
if hasattr(sys.stdout, 'reconfigure'):
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from gsheet_auth import get_client, get_sheet_id
from sheet_updater import GID_ANALYSIS

def main():
    client = get_client()
    doc = client.open_by_key(get_sheet_id())
    ws = None
    for sheet in doc.worksheets():
        if sheet.id == GID_ANALYSIS:
            ws = sheet
            break
            
    if ws is None:
        print("Sheet not found")
        return
        
    print(f"Row 4:")
    row_vals = ws.row_values(4)
    for i, val in enumerate(row_vals):
        print(f"  Col {i+1} ({chr(65+i) if i < 26 else '...'}): {val}")

if __name__ == "__main__":
    main()
