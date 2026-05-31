import sys
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from valuation_app.audit import run_audit
from valuation_app.repository import load_market_data, load_metric_observations

def compare_metrics(ticker: str):
    # Load GuruFocus
    gf_path = ROOT / "data" / "gurufocus_context" / f"{ticker}.json"
    if not gf_path.exists():
        print(f"[{ticker}] GuruFocus 데이터가 없습니다. 먼저 ingest_gurufocus.py를 실행하세요.")
        return
        
    with open(gf_path, "r", encoding="utf-8") as f:
        gf_data = json.load(f)
        
    # Load Local Valuation App
    metrics_path = ROOT / "data" / "valuation" / ticker / "normalized" / "metrics.json"
    market_path = ROOT / "data" / "valuation" / ticker / "normalized" / "market.json"
    
    if not metrics_path.exists() or not market_path.exists():
        print(f"[{ticker}] 로컬 Valuation 데이터가 없습니다.")
        return
        
    observations = load_metric_observations(metrics_path)
    market = load_market_data(market_path)
    input_set, checks, derived = run_audit(observations, market)
    inp = input_set.inputs
    
    print(f"=== {ticker} 지표 비교 ===")
    print(f"1. ROIC")
    gf_roic = gf_data.get("roic_pct", "N/A")
    local_roic = inp.get("roic")
    local_roic_pct = round(local_roic * 100, 2) if local_roic is not None else "N/A"
    print(f"  - GuruFocus : {gf_roic} %")
    print(f"  - Local App : {local_roic_pct} %")
    
    print(f"2. FCF Margin")
    gf_fcf_m = gf_data.get("fcf_margin_pct", "N/A")
    local_rev = inp.get("revenue")
    local_fcf = inp.get("fcf")
    if local_rev and local_fcf:
        local_fcf_m = round(local_fcf / local_rev * 100, 2)
    else:
        local_fcf_m = "N/A"
    print(f"  - GuruFocus : {gf_fcf_m} %")
    print(f"  - Local App : {local_fcf_m} %")
    
    print(f"3. EV/FCF")
    gf_ev_fcf = gf_data.get("ev_to_fcf", "N/A")
    local_ev = inp.get("enterprise_value")
    if local_ev and local_fcf:
        local_ev_fcf = round(local_ev / local_fcf, 2)
    else:
        local_ev_fcf = "N/A"
    print(f"  - GuruFocus : {gf_ev_fcf}")
    print(f"  - Local App : {local_ev_fcf}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        compare_metrics(sys.argv[1])
    else:
        compare_metrics("ADBE")
