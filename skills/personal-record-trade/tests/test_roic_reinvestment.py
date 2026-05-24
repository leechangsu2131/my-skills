import pytest

from valuation_app.roic_reinvestment import (
    build_reinvestment_matrix,
    calc_economic_profit,
    calc_ev_nopat_multiple,
    calc_growth_from_reinvestment,
    calc_implied_roic_from_value_driver,
    calc_reinvestment_rate,
)


def test_calc_ev_nopat_multiple():
    multiple = calc_ev_nopat_multiple(100_809_295_265_792, 746_191_572_614)

    assert multiple == pytest.approx(135.0984103354)


def test_calc_ev_nopat_multiple_returns_none_when_nopat_is_zero_or_negative():
    assert calc_ev_nopat_multiple(100, 0) is None
    assert calc_ev_nopat_multiple(100, -1) is None


def test_calc_implied_roic_from_value_driver_matches_mckinsey_example():
    implied_roic = calc_implied_roic_from_value_driver(
        ev_nopat_multiple=20,
        wacc=0.09,
        growth_rate=0.05,
    )

    assert implied_roic == pytest.approx(0.25)


def test_calc_implied_roic_returns_none_when_denominator_is_not_positive():
    assert calc_implied_roic_from_value_driver(135.0984103354, 0.09, 0.03) is None
    assert calc_implied_roic_from_value_driver(20, 0.03, 0.03) is None


def test_calc_reinvestment_rate_and_growth_from_reinvestment():
    assert calc_reinvestment_rate(0.05, 0.25) == pytest.approx(0.20)
    assert calc_reinvestment_rate(0.05, 0) is None
    assert calc_growth_from_reinvestment(0.25, 0.20) == pytest.approx(0.05)


def test_calc_economic_profit():
    economic_profit = calc_economic_profit(
        nopat=746_191_572_614,
        invested_capital=9_117_746_517_534,
        wacc=0.09,
    )

    assert economic_profit == pytest.approx(-74_405_613_964.06)


def test_build_reinvestment_matrix():
    rows = build_reinvestment_matrix(
        growth_rates=[0.03, 0.05],
        roic_values=[0.10, 0.25],
    )

    assert rows[0]["growth_rate"] == 0.03
    assert rows[0][0.10] == pytest.approx(0.30)
    assert rows[1][0.25] == pytest.approx(0.20)
