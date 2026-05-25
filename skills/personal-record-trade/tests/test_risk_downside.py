import pytest

from valuation_app.risk_downside import (
    build_margin_wacc_sensitivity,
    build_risk_metric_explanations,
    build_scenario_table,
    build_wacc_growth_sensitivity,
    calc_ev_gap,
    calc_implied_ev,
    rank_value_drivers,
)


# --- calc_implied_ev ---


def test_calc_implied_ev_basic():
    # FCF=1000, WACC=10%, g=3% → EV = 1000 / 0.07 ≈ 14285.71
    ev = calc_implied_ev(1000, 0.10, 0.03)
    assert ev == pytest.approx(1000 / 0.07)


def test_calc_implied_ev_returns_none_when_wacc_le_growth():
    assert calc_implied_ev(1000, 0.03, 0.03) is None
    assert calc_implied_ev(1000, 0.02, 0.03) is None


def test_calc_implied_ev_with_real_scale():
    # Normalized FCF ≈ 807B, WACC=9%, g=3%
    fcf = 807_525_087_600
    ev = calc_implied_ev(fcf, 0.09, 0.03)
    assert ev == pytest.approx(807_525_087_600 / 0.06)


# --- calc_ev_gap ---


def test_calc_ev_gap_positive():
    # implied > current → positive gap
    gap = calc_ev_gap(120, 100)
    assert gap == pytest.approx(0.20)


def test_calc_ev_gap_negative():
    # implied < current → negative gap
    gap = calc_ev_gap(80, 100)
    assert gap == pytest.approx(-0.20)


def test_calc_ev_gap_returns_none_for_invalid():
    assert calc_ev_gap(None, 100) is None
    assert calc_ev_gap(100, 0) is None


# --- build_wacc_growth_sensitivity ---


def test_build_wacc_growth_sensitivity_implied_ev():
    rows = build_wacc_growth_sensitivity(
        base_revenue=11_314_459_238_100,
        operating_margin=0.11,
        tax_rate=0.183,
        fcf_conversion=0.70,
        wacc_values=[0.08, 0.10],
        growth_values=[0.02, 0.03],
        current_ev=100_809_295_265_792,
        metric="implied_ev",
    )

    assert len(rows) == 2
    assert rows[0]["wacc"] == 0.08
    # Check that EV values are present and positive
    assert rows[0][0.02] is not None
    assert rows[0][0.02] > 0
    assert rows[1][0.03] is not None


def test_build_wacc_growth_sensitivity_ev_gap():
    rows = build_wacc_growth_sensitivity(
        base_revenue=11_314_459_238_100,
        operating_margin=0.11,
        tax_rate=0.183,
        fcf_conversion=0.70,
        wacc_values=[0.09],
        growth_values=[0.03],
        current_ev=100_809_295_265_792,
        metric="ev_gap",
    )

    assert len(rows) == 1
    # Gap should be a ratio
    assert rows[0][0.03] is not None
    assert isinstance(rows[0][0.03], float)


def test_build_wacc_growth_sensitivity_rejects_unknown_metric():
    with pytest.raises(ValueError, match="metric must be"):
        build_wacc_growth_sensitivity(
            base_revenue=100,
            operating_margin=0.1,
            tax_rate=0.2,
            fcf_conversion=0.7,
            wacc_values=[0.09],
            growth_values=[0.03],
            current_ev=100,
            metric="bad_metric",
        )


# --- build_margin_wacc_sensitivity ---


def test_build_margin_wacc_sensitivity():
    rows = build_margin_wacc_sensitivity(
        base_revenue=11_314_459_238_100,
        tax_rate=0.183,
        fcf_conversion=0.70,
        margin_values=[0.08, 0.12],
        wacc_values=[0.08, 0.10],
        terminal_growth=0.03,
        current_ev=100_809_295_265_792,
        metric="ev_gap",
    )

    assert len(rows) == 2
    assert rows[0]["margin"] == 0.08
    assert rows[1]["margin"] == 0.12
    # Higher margin should yield higher (less negative) gap
    assert rows[1][0.08] > rows[0][0.08]


# --- build_scenario_table ---


def test_build_scenario_table():
    scenarios = [
        {"name": "베어", "revenue_growth": 0.0, "operating_margin": 0.08, "wacc": 0.11, "terminal_growth": 0.02},
        {"name": "베이스", "revenue_growth": 0.10, "operating_margin": 0.12, "wacc": 0.09, "terminal_growth": 0.03},
        {"name": "불", "revenue_growth": 0.30, "operating_margin": 0.18, "wacc": 0.08, "terminal_growth": 0.03},
    ]

    results = build_scenario_table(
        base_revenue=11_314_459_238_100,
        scenarios=scenarios,
        tax_rate=0.183,
        fcf_conversion=0.70,
        current_ev=100_809_295_265_792,
    )

    assert len(results) == 3
    assert results[0]["시나리오"] == "베어"
    assert results[1]["시나리오"] == "베이스"
    assert results[2]["시나리오"] == "불"

    # Bull EV should be > Base EV > Bear EV
    assert results[2]["추정 EV"] > results[1]["추정 EV"] > results[0]["추정 EV"]

    # Bear gap should be most negative
    assert results[0]["현재 EV 대비 괴리율"] < results[1]["현재 EV 대비 괴리율"]


# --- rank_value_drivers ---


def test_rank_value_drivers_returns_sorted():
    drivers = rank_value_drivers(
        base_revenue=11_314_459_238_100,
        base_margin=0.11,
        base_tax_rate=0.183,
        base_fcf_conversion=0.70,
        base_wacc=0.09,
        base_terminal_growth=0.03,
        current_ev=100_809_295_265_792,
        delta=0.01,
    )

    assert len(drivers) == 5
    # Should be sorted by absolute EV change descending
    abs_changes = [abs(d["EV 변화"]) for d in drivers if d["EV 변화"] is not None]
    assert abs_changes == sorted(abs_changes, reverse=True)


def test_rank_value_drivers_all_have_required_keys():
    drivers = rank_value_drivers(
        base_revenue=11_314_459_238_100,
        base_margin=0.11,
        base_tax_rate=0.183,
        base_fcf_conversion=0.70,
        base_wacc=0.09,
        base_terminal_growth=0.03,
        current_ev=100_809_295_265_792,
    )

    required_keys = {"변수", "기준값", "변동폭", "기준 EV", "변동 EV", "EV 변화", "EV 변화율"}
    for driver in drivers:
        assert required_keys.issubset(driver.keys())


# --- build_risk_metric_explanations ---


def test_build_risk_metric_explanations_are_beginner_friendly():
    rows = build_risk_metric_explanations()

    assert rows[0]["지표"] == "추정 EV"
    assert "현재 EV" in rows[0]["어떻게 읽나"]
    assert any(row["지표"] == "괴리율" for row in rows)
    assert any(row["지표"] == "가치 동인 순위" for row in rows)
    assert any(row["지표"] == "베어/베이스/불" for row in rows)
