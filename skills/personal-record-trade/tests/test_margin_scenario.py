import pytest

from valuation_app.margin_scenario import (
    build_margin_scenario_matrix,
    build_required_margin_table,
    calc_required_operating_margin,
    calc_required_revenue,
)


def test_calc_required_operating_margin_for_required_fcf():
    margin = calc_required_operating_margin(
        required_fcf=6_048_557_715_947.52,
        revenue=11_314_459_238_100,
        tax_rate=0.183,
        fcf_conversion=0.70,
    )

    assert margin == pytest.approx(0.9347552873)


def test_calc_required_operating_margin_returns_none_when_denominator_is_zero():
    assert calc_required_operating_margin(100, revenue=0, tax_rate=0.183, fcf_conversion=0.70) is None
    assert calc_required_operating_margin(100, revenue=100, tax_rate=1.0, fcf_conversion=0.70) is None
    assert calc_required_operating_margin(100, revenue=100, tax_rate=0.183, fcf_conversion=0) is None


def test_calc_required_revenue_for_required_fcf():
    revenue = calc_required_revenue(
        required_fcf=6_048_557_715_947.52,
        operating_margin=0.25,
        tax_rate=0.183,
        fcf_conversion=0.70,
    )

    assert revenue == pytest.approx(42_305_002_384_665.29)


def test_build_required_margin_table_shows_growth_cases():
    rows = build_required_margin_table(
        base_revenue=11_314_459_238_100,
        required_fcf=6_048_557_715_947.52,
        growth_rates=[0.0, 0.2],
        tax_rate=0.183,
        fcf_conversion=0.70,
    )

    assert rows[0]["growth_rate"] == 0.0
    assert rows[0]["scenario_revenue"] == pytest.approx(11_314_459_238_100)
    assert rows[0]["required_operating_margin"] == pytest.approx(0.9347552873)
    assert rows[1]["scenario_revenue"] == pytest.approx(13_577_351_085_720)
    assert rows[1]["required_operating_margin"] == pytest.approx(0.7789627394)


def test_build_margin_scenario_matrix_returns_required_fcf_coverage():
    rows = build_margin_scenario_matrix(
        base_revenue=11_314_459_238_100,
        required_fcf=6_048_557_715_947.52,
        growth_rates=[0.0, 0.2],
        operating_margins=[0.1, 0.25],
        tax_rate=0.183,
        fcf_conversion=0.70,
    )

    assert rows[0]["growth_rate"] == 0.0
    assert rows[0][0.1] == pytest.approx(0.1069798709)
    assert rows[1][0.25] == pytest.approx(0.3209396128)
