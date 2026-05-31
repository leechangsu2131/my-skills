import sys
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from valuation_app.audit import run_audit
from valuation_app.repository import load_market_data, load_metric_observations
from sheet_updater import _safe_ratio, _yoy_growth

def compare_fc():
    ticker = "NVDA"
    fc_txt_path = ROOT / "financecharts_test.txt"
    if not fc_txt_path.exists():
        print("financecharts_test.txt not found.")
        return
        
    text = fc_txt_path.read_text(encoding="utf-8")
    
    # Load Local Valuation App
    metrics_path = ROOT / "data" / "valuation" / ticker / "normalized" / "metrics.json"
    market_path = ROOT / "data" / "valuation" / ticker / "normalized" / "market.json"
    observations = load_metric_observations(metrics_path)
    market = load_market_data(market_path)
    input_set, checks, derived = run_audit(observations, market)
    all_observations = observations + derived
    inp = input_set.inputs
    
    # Extract from FC
    def extract_val(pattern):
        match = re.search(pattern, text)
        if match:
            val_str = match.group(1).replace(',', '').replace('%', '')
            try:
                return float(val_str)
            except ValueError:
                return None
        return None
        
    fc_pe = extract_val(r'PE RATIO\n([0-9,.]+)')
    fc_ps = extract_val(r'PS RATIO\n([0-9,.]+)')
    fc_pb = extract_val(r'PB RATIO\n([0-9,.]+)')
    fc_ev_ebitda = extract_val(r'EV/EBITDA RATIO\n([0-9,.]+)')
    fc_roa = extract_val(r'ROA\n([0-9,.]+)')
    fc_roe = extract_val(r'ROE\n([0-9,.]+)')
    fc_roic = extract_val(r'ROIC\n([0-9,.]+)')
    fc_fcf_yield = extract_val(r'FCF YIELD\n([0-9,.]+)')
    fc_earnings_yield = extract_val(r'EARNINGS YIELD\n([0-9,.]+)')
    
    # Local calculations
    local_pe = _safe_ratio(market.get("market_cap"), inp.get("net_income"))
    local_ps = _safe_ratio(market.get("market_cap"), inp.get("revenue"))
    local_pb = _safe_ratio(market.get("market_cap"), inp.get("total_equity"))
    
    local_ebitda = inp.get("operating_income") + inp.get("depreciation_and_amortization", 0) if inp.get("operating_income") else None
    local_ev_ebitda = _safe_ratio(inp.get("enterprise_value"), local_ebitda)
    
    local_roa = _safe_ratio(inp.get("net_income"), inp.get("total_assets"), pct=True)
    local_roe = _safe_ratio(inp.get("net_income"), inp.get("total_equity"), pct=True)
    local_roic = round(inp.get("roic") * 100, 2) if inp.get("roic") else ""
    
    local_fcf_yield = _safe_ratio(inp.get("fcf"), market.get("market_cap"), pct=True)
    local_earnings_yield = _safe_ratio(inp.get("net_income"), market.get("market_cap"), pct=True)

    print(f"=== NVDA 지표 교차 검증 (FinanceCharts vs Local App) ===")
    print(f"{'Metric':<20} | {'FinanceCharts':<15} | {'Local App':<15} | {'Difference'}")
    print("-" * 75)
    
    def print_row(name, fc_v, local_v, is_pct=False):
        fc_str = f"{fc_v:.2f}" if fc_v is not None else "N/A"
        if is_pct and fc_v is not None: fc_str += "%"
        
        local_str = f"{local_v}" if local_v != "" else "N/A"
        if is_pct and local_v != "": local_str += "%"
        
        diff = ""
        if fc_v is not None and local_v != "":
            diff_val = abs(fc_v - float(local_v))
            if diff_val < 1.0:
                diff = "✅ Almost identical"
            elif diff_val < 5.0:
                diff = "⚠️ Minor diff"
            else:
                diff = "❌ Large diff"
                
        print(f"{name:<20} | {fc_str:<15} | {local_str:<15} | {diff}")

    print_row("P/E Ratio", fc_pe, local_pe)
    print_row("P/S Ratio", fc_ps, local_ps)
    print_row("P/B Ratio", fc_pb, local_pb)
    print_row("EV / EBITDA", fc_ev_ebitda, local_ev_ebitda)
    print_row("ROA", fc_roa, local_roa, is_pct=True)
    print_row("ROE", fc_roe, local_roe, is_pct=True)
    print_row("ROIC", fc_roic, local_roic, is_pct=True)
    print_row("FCF Yield", fc_fcf_yield, local_fcf_yield, is_pct=True)
    print_row("Earnings Yield", fc_earnings_yield, local_earnings_yield, is_pct=True)

if __name__ == "__main__":
    compare_fc()
