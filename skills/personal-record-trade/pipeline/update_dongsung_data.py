import sys
import json
from pathlib import Path
import datetime

ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, 'reconfigure'):
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

import pipeline.layer1_store as L

def update_dongsung_data():
    ticker = "033500"
    
    # 1. Update "기업분석" JSON payload (for update_forecasts.py)
    # Based on Shinhan Securities 2026.06.05
    report_data = {
        "ticker": ticker,
        "investment_opinion": "Buy",
        "target_price": 33000,
        "consensus_metrics": {
            "op": 11.3, # 영업이익률 OPM
            "eps": 2638,
            "roe": 27.1,
            "f_per": 8.2,
            "revenue": "" # Not extracted
        }
    }
    
    out_dir = ROOT / "data" / "report_context"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{ticker}_1.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)
    print(f"✅ Created {json_path.name} for 기업분석 탭 업데이트.")
    
    # 2. Update "raw data" tab via layer1_store
    raw_metrics = {
        "op_margin": 11.3,
        "roic": 44.4,
        "fwd_pe_fy": 8.2,
        "fwd_pe_ntm": 8.2
    }
    
    # Call save_row which writes to JSONL and upserts to "raw data" sheet
    L.save_row(ticker, "analyst", raw_metrics)
    print(f"✅ layer1_store.save_row 를 통해 'raw data' 탭 업데이트/저장 완료.")
    
if __name__ == "__main__":
    update_dongsung_data()
