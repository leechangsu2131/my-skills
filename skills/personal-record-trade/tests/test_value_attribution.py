import pytest

from valuation_app.value_attribution import (
    build_value_attribution_table,
    calc_future_expectation_ratio,
    calc_future_expectation_value,
    calc_no_growth_value,
)


def test_calc_no_growth_value_capitalizes_current_nopat():
    assert calc_no_growth_value(746_191_572_614, 0.09) == pytest.approx(8_291_017_473_488.89)


def test_calc_no_growth_value_rejects_non_positive_wacc():
    with pytest.raises(ValueError, match="WACC must be positive"):
        calc_no_growth_value(100, 0)


def test_future_expectation_value_and_ratio():
    no_growth_value = calc_no_growth_value(746_191_572_614, 0.09)
    future_value = calc_future_expectation_value(100_809_295_265_792, no_growth_value)

    assert future_value == pytest.approx(92_518_277_792_303.11)
    assert calc_future_expectation_ratio(future_value, 100_809_295_265_792) == pytest.approx(0.9177554267)


def test_future_expectation_ratio_returns_none_when_ev_is_zero():
    assert calc_future_expectation_ratio(100, 0) is None


def test_build_value_attribution_table():
    rows = build_value_attribution_table(
        enterprise_value=100_809_295_265_792,
        nopat=746_191_572_614,
        wacc_values=[0.07, 0.09, 0.11],
    )

    assert len(rows) == 3
    assert rows[0]["wacc"] == 0.07
    assert rows[0]["no_growth_value"] == pytest.approx(10_659_879_608_771.43)
    assert rows[1]["future_expectation_ratio"] == pytest.approx(0.9177554267)
    assert rows[2]["future_expectation_ratio"] == pytest.approx(0.9327089855)
