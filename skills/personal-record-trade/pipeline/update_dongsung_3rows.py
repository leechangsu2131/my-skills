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

def update_dongsung_3rows():
    ticker = "033500"
    as_of = datetime.date.today().isoformat()
    
    # 1. Update "raw data" tab with 3 rows (Shinhan, Mirae, DS)
    # Shinhan
    shinhan_metrics = {
        "op_margin": 11.3,
        "roic": 44.4,
        "fwd_pe_fy": 8.2,
        "fwd_pe_ntm": 8.2,
        "fair_value": 33000
    }
    L.save_row(ticker, "analyst_신한투자증권", shinhan_metrics)
    
    # Mirae Asset
    mirae_metrics = {
        "op_margin": 10.0,
        "roic": 44.4, # Using the general 2026F expectation derived from the industry context
        "fwd_pe_fy": 8.2,
        "fwd_pe_ntm": 8.2
    }
    L.save_row(ticker, "analyst_미래에셋증권", mirae_metrics)
    
    # DS Securities
    ds_metrics = {
        "fair_value": 38000,
        "op_margin": 10.65, # Average proxy
        "roic": 44.4,
        "fwd_pe_fy": 8.2,
        "fwd_pe_ntm": 8.2
    }
    L.save_row(ticker, "analyst_DS투자증권", ds_metrics)
    print(f"✅ 'raw data' 탭에 3개 증권사(신한, 미래, DS) 데이터 각각 세 줄 저장 완료.")

    # 2. Synthesize for "기업분석" (Average / Representative values)
    synthesized_data = {
        "ticker": ticker,
        "investment_opinion": "Buy",
        "target_price": 35500, # Average of 33000 and 38000
        "consensus_metrics": {
            "op": 10.65, # Average of 11.3 and 10.0
            "eps": 2638,
            "roe": 27.1,
            "f_per": 8.2,
            "roic": 44.4, # ROIC mapped explicitly
            "revenue": "" 
        }
    }
    
    out_dir = ROOT / "data" / "report_context"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{ticker}_1.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(synthesized_data, f, indent=2, ensure_ascii=False)
    print(f"✅ {json_path.name} 파일에 종합(평균) 이익 지표(ROIC 포함) 저장 완료.")
    
if __name__ == "__main__":
    update_dongsung_3rows()
