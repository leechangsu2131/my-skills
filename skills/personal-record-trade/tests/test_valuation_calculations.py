import pytest

from valuation_app.calculations import (
    calc_enterprise_value,
    calc_fcf,
    calc_invested_capital,
    calc_net_debt,
    calc_nopat,
    calc_required_fcf,
    calc_roic,
)


def test_calc_fcf_uses_positive_capex_outflow():
    assert calc_fcf(1_490_090_883_050, 1_246_323_544_400) == 243_767_338_650


def test_calc_net_debt_can_be_negative_for_net_cash_company():
    assert calc_net_debt(0, 2_277_190_926_336, 2_701_205_962_752) == -424_015_036_416


def test_calc_enterprise_value_from_market_cap_and_net_debt():
    ev = calc_enterprise_value(
        market_cap=101_233_310_302_208,
        net_debt=-424_015_036_416,
    )
    assert ev == 100_809_295_265_792


def test_calc_nopat_and_invested_capital_and_roic():
    nopat = calc_nopat(913_331_178_230, 0.183)
    invested_capital = calc_invested_capital(9_541_761_553_950, -424_015_036_416)
    roic = calc_roic(nopat, invested_capital)

    assert round(nopat) == 746_191_572_614
    assert invested_capital == 9_117_746_517_534
    assert round(roic, 4) == 0.0818


def test_calc_roic_returns_none_when_invested_capital_is_zero():
    assert calc_roic(100, 0) is None


def test_calc_required_fcf():
    assert calc_required_fcf(100_809_295_265_792, 0.09, 0.03) == pytest.approx(
        6_048_557_715_947.52
    )


def test_calc_required_fcf_rejects_invalid_terminal_spread():
    with pytest.raises(ValueError, match="WACC must be greater"):
        calc_required_fcf(100, 0.03, 0.03)
