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
    assert input_set.inputs["market_cap"] == market["market_cap"]
    assert input_set.inputs["fcf"] is not None
    assert input_set.inputs["latest_quarter_revenue"] is not None


def test_run_audit_calculates_passes_and_warning_for_reported_ev_gap():
    observations, market = _load_seed()
    input_set, checks, derived = run_audit(observations, market)
    statuses = {check.check_key: check.status for check in checks}
    derived_map = {obs.metric_key: obs.value for obs in derived}

    assert "fcf_reconciliation" in statuses
    assert "net_debt_reconciliation" in statuses
    assert "reported_ev_gap" in statuses
    assert "operating_margin_consistency" in statuses
    assert "fcf_vs_op_cashflow" in statuses
    assert "revenue_vs_operating_income" in statuses
    assert "currency_unit_consistency" in statuses
    assert "current_per_anomaly" in statuses
    assert "enterprise_value" in derived_map
    assert "roic" in derived_map
    assert input_set.inputs["enterprise_value"] == derived_map["enterprise_value"]


def test_observation_map_selects_latest_annual():
    from valuation_app.models import MetricObservation
    from valuation_app.audit import _observation_map

    obs_list = [
        MetricObservation(
            metric_key="revenue", label="Rev", value=100, period="2021A", source_method="rule", confidence=1.0
        ),
        MetricObservation(
            metric_key="revenue", label="Rev", value=200, period="2025A", source_method="rule", confidence=1.0
        ),
        MetricObservation(
            metric_key="revenue", label="Rev", value=150, period="2023A", source_method="rule", confidence=1.0
        ),
        MetricObservation(
            metric_key="revenue", label="Rev", value=999, period="2026Q1", source_method="rule", confidence=1.0
        ),
    ]

    mapped = _observation_map(obs_list)
    # A로 끝나는 연간 데이터 중 2025A가 가장 최신이므로 value가 200인 것이 선택되어야 함.
    assert mapped["revenue"].value == 200
    assert mapped["revenue"].period == "2025A"


def test_new_audit_checks_validation():
    from valuation_app.models import MetricObservation
    
    # 1. 영업마진 일관성 에러 케이스: 영업이익 > 매출액
    obs_fail = [
        MetricObservation(metric_key="revenue", label="Rev", value=100, period="2025A", source_method="rule", confidence=1.0),
        MetricObservation(metric_key="operating_income", label="OpInc", value=150, period="2025A", source_method="rule", confidence=1.0),
    ]
    market = {"ticker": "TEST", "company_name": "Test", "valuation_date": "2026-05-31", "price": 10.0, "shares_outstanding": 100.0, "market_cap": 1000.0}
    _, checks, _ = run_audit(obs_fail, market)
    statuses = {c.check_key: c.status for c in checks}
    assert statuses["operating_margin_consistency"] == "fail"

    # 2. 영업마진 일관성 경고 케이스: 영업적자
    obs_warn = [
        MetricObservation(metric_key="revenue", label="Rev", value=100, period="2025A", source_method="rule", confidence=1.0),
        MetricObservation(metric_key="operating_income", label="OpInc", value=-10, period="2025A", source_method="rule", confidence=1.0),
    ]
    _, checks, _ = run_audit(obs_warn, market)
    statuses = {c.check_key: c.status for c in checks}
    assert statuses["operating_margin_consistency"] == "warning"

    # 3. FCF vs 영업현금흐름 에러 케이스: FCF > 영업현금흐름
    obs_fcf_fail = [
        MetricObservation(metric_key="op_cashflow", label="OpCash", value=100, period="2025A", source_method="rule", confidence=1.0),
        MetricObservation(metric_key="capex", label="Capex", value=10, period="2025A", source_method="rule", confidence=1.0),
        MetricObservation(metric_key="fcf", label="FCF", value=120, period="2025A", source_method="rule", confidence=1.0),
    ]
    _, checks, _ = run_audit(obs_fcf_fail, market)
    statuses = {c.check_key: c.status for c in checks}
    assert statuses["fcf_vs_op_cashflow"] == "fail"

    # 4. 통화 단위 불일치 에러 케이스: USD 주식인데 KRW 단위 지표
    obs_unit_fail = [
        MetricObservation(metric_key="revenue", label="Rev", value=100, period="2025A", unit="KRW", source_method="rule", confidence=1.0),
    ]
    market_usd = {"ticker": "TEST", "company_name": "Test", "valuation_date": "2026-05-31", "price": 10.0, "shares_outstanding": 100.0, "market_cap": 1000.0, "currency": "USD"}
    _, checks, _ = run_audit(obs_unit_fail, market_usd)
    statuses = {c.check_key: c.status for c in checks}
    assert statuses["currency_unit_consistency"] == "fail"

    # 5. 현재 PER 이상치 경고 케이스: PER > 300
    obs_per_anomaly = [
        MetricObservation(metric_key="eps", label="EPS", value=0.01, period="2025A", unit="USD", source_method="rule", confidence=1.0),
    ]
    market_high_per = {"ticker": "TEST", "company_name": "Test", "valuation_date": "2026-05-31", "price": 5.0, "shares_outstanding": 100.0, "market_cap": 500.0, "currency": "USD"}
    _, checks, _ = run_audit(obs_per_anomaly, market_high_per)
    statuses = {c.check_key: c.status for c in checks}
    assert statuses["current_per_anomaly"] == "warning"


