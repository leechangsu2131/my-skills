from pathlib import Path

from valuation_app.audit import build_input_set, run_audit
from valuation_app.repository import load_market_data, load_metric_observations


ROOT = Path(__file__).resolve().parents[1]


def _load_seed():
    observations = load_metric_observations(ROOT / "data/valuation/009150/normalized/metrics.json")
    market = load_market_data(ROOT / "data/valuation/009150/normalized/market.json")
    return observations, market


def test_build_input_set_includes_market_and_financial_inputs():
    observations, market = _load_seed()
    input_set = build_input_set(observations, market)

    assert input_set.ticker == "009150"
    assert input_set.inputs["market_cap"] == 101_233_310_302_208
    assert input_set.inputs["fcf"] == 243_767_338_650
    assert input_set.inputs["latest_quarter_revenue"] == 3_209_100_000_000


def test_run_audit_calculates_passes_and_warning_for_reported_ev_gap():
    observations, market = _load_seed()
    input_set, checks, derived = run_audit(observations, market)
    statuses = {check.check_key: check.status for check in checks}
    derived_map = {obs.metric_key: obs.value for obs in derived}

    assert statuses["fcf_reconciliation"] == "pass"
    assert statuses["net_debt_reconciliation"] == "pass"
    assert statuses["reported_ev_gap"] == "warning"
    assert derived_map["enterprise_value"] == 100_809_295_265_792
    assert round(derived_map["roic"], 4) == 0.0818
    assert input_set.inputs["enterprise_value"] == 100_809_295_265_792
