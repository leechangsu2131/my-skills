import sys
import json
from pathlib import Path
from gspread.utils import rowcol_to_a1

ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, 'reconfigure'):
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

from gsheet_auth import get_client, get_sheet_id
from sheet_updater import _find_ticker_row, GID_ANALYSIS

def main():
    client = get_client()
    doc = client.open_by_key(get_sheet_id())
    
    ws = None
    for sheet in doc.worksheets():
        if sheet.id == GID_ANALYSIS:
            ws = sheet
            break
            
    if ws is None:
        print("❌ 기업분석 탭을 찾을 수 없습니다.")
        return
        
    # Check headers in row 4
    headers = ws.row_values(4)
    expected_new_headers = ['애널목표가', '투자의견', '예상매출', '예상OP', '예상EPS', '예상ROE', 'F_PER']
    
    # Expand columns if needed
    if ws.col_count < len(headers) + len(expected_new_headers) + 2:
        try:
            ws.add_cols(10)
            print("📈 시트 컬럼 수를 확장했습니다.")
        except Exception as e:
            print(f"⚠️ 컬럼 확장 실패: {e}")

    # Append missing headers
    updates = []
    start_col = len(headers) + 1
    
    for i, h in enumerate(expected_new_headers):
        if h not in headers:
            col_letter = rowcol_to_a1(4, start_col + i)[0] # column letter
            updates.append({"range": f"{col_letter}4", "values": [[h]]})
    
    if updates:
        ws.batch_update(updates, value_input_option="USER_ENTERED")
        print("✅ 새 컬럼 헤더를 추가했습니다.")
        headers = ws.row_values(4) # refresh headers

    # Create mapping of header to column index (1-based)
    col_map = {h: i+1 for i, h in enumerate(headers)}
    
    # Process all JSONs
    report_dir = ROOT / "data" / "report_context"
    data_updates = []
    
    for file in report_dir.glob("*.json"):
        ticker = file.stem.split('_')[0]
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            row = _find_ticker_row(ws, ticker)
            if row is None:
                print(f"⚠️ 시트에서 {ticker} 종목을 찾지 못했습니다.")
                continue
                
            # Prepare updates
            tp = data.get("target_price", "")
            opinion = data.get("investment_opinion", "")
            cm = data.get("consensus_metrics", {})
            
            val_map = {
                '애널목표가': tp,
                '투자의견': opinion,
                '예상매출': cm.get("revenue", ""),
                '예상OP': cm.get("op", ""),
                '예상EPS': cm.get("eps", ""),
                '예상ROE': cm.get("roe", ""),
                'F_PER': cm.get("f_per", ""),
                'ROIC%': cm.get("roic", ""),
                '영업마진%': cm.get("op", "")
            }
            
            for k, v in val_map.items():
                if k in col_map:
                    col_idx = col_map[k]
                    col_letter = rowcol_to_a1(row, col_idx).replace(str(row), '')
                    data_updates.append({"range": f"{col_letter}{row}", "values": [[v]]})
                    
        except Exception as e:
            print(f"⚠️ {file.name} 처리 중 에러: {e}")
            
    if data_updates:
        ws.batch_update(data_updates, value_input_option="USER_ENTERED")
        print(f"🎉 성공적으로 {len(data_updates)}개의 전망치 데이터 셀을 업데이트했습니다!")
    else:
        print("업데이트할 데이터가 없습니다.")

if __name__ == "__main__":
    main()
