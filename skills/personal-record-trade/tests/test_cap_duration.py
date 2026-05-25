import pytest

from valuation_app.cap_duration import (
    build_cap_duration_table,
    build_cap_metric_explanations,
    calc_annual_economic_profit_from_roic,
    calc_discounted_cap_years,
    calc_discounted_economic_profit_value,
    calc_simple_payback_years,
)


def test_calc_annual_economic_profit_from_roic():
    economic_profit = calc_annual_economic_profit_from_roic(
        invested_capital=9_117_746_517_534,
        roic=0.20,
        wacc=0.09,
    )

    assert economic_profit == pytest.approx(1_002_952_116_928.74)


def test_discounted_economic_profit_value():
    value = calc_discounted_economic_profit_value(
        annual_economic_profit=1_000_000_000_000,
        wacc=0.09,
        years=10,
    )

    assert value == pytest.approx(6_417_657_731_601.74)


def test_calc_simple_payback_years():
    years = calc_simple_payback_years(
        excess_value=92_518_277_792_303.11,
        annual_economic_profit=5_500_000_000_000,
    )

    assert years == pytest.approx(16.8215050531)


def test_discounted_cap_years_returns_none_when_perpetuity_is_too_small():
    assert calc_discounted_cap_years(
        excess_value=92_518_277_792_303.11,
        annual_economic_profit=5_500_000_000_000,
        wacc=0.09,
    ) is None


def test_discounted_cap_years_solves_finite_annuity():
    years = calc_discounted_cap_years(
        excess_value=60,
        annual_economic_profit=10,
        wacc=0.10,
    )

    assert years == pytest.approx(9.6137761334)


def test_cap_functions_return_none_for_invalid_inputs():
    assert calc_simple_payback_years(100, 0) is None
    assert calc_discounted_economic_profit_value(100, 0.09, 0) is None
    assert calc_discounted_cap_years(100, 10, 0) is None


def test_build_cap_duration_table():
    rows = build_cap_duration_table(
        excess_value=92_518_277_792_303.11,
        invested_capital=9_117_746_517_534,
        roic_values=[0.20, 0.70],
        wacc=0.09,
        periods=[5, 10],
    )

    assert len(rows) == 2
    assert rows[0]["roic"] == 0.20
    assert rows[0]["annual_economic_profit"] == pytest.approx(1_002_952_116_928.74)
    assert rows[0]["simple_payback_years"] == pytest.approx(92.2459569412)
    assert rows[0]["discounted_cap_years"] is None
    assert rows[1][5] == pytest.approx(21_633_561_099_116.59)
    assert rows[1][10] == pytest.approx(35_693_891_454_835.39)


def test_build_cap_metric_explanations_are_beginner_friendly():
    rows = build_cap_metric_explanations()

    assert rows[0]["지표"] == "초과가치"
    assert "현재 수익력" in rows[0]["무슨 뜻인가"]
    assert any(row["지표"] == "할인 CAP" and "불가능" in row["어떻게 읽나"] for row in rows)
