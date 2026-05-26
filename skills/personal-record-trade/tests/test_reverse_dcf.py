import pytest

from valuation_app.reverse_dcf import (
    build_required_fcf_matrix,
    build_required_fcf_table,
    calc_normalized_fcf,
    required_fcf_multiple,
)


def test_required_fcf_multiple_handles_current_fcf():
    assert required_fcf_multiple(6_048_557_715_947.52, 243_767_338_650) == pytest.approx(24.8128307486)


def test_required_fcf_multiple_returns_none_when_current_fcf_is_zero_or_missing():
    assert required_fcf_multiple(100, 0) is None
    assert required_fcf_multiple(100, None) is None


def test_build_required_fcf_table_uses_wacc_growth_pairs():
    rows = build_required_fcf_table(
        enterprise_value=100_809_295_265_792,
        current_fcf=243_767_338_650,
        wacc_values=[0.07, 0.09],
        terminal_growth_values=[0.02, 0.03],
    )

    assert len(rows) == 4
    assert rows[0]["wacc"] == 0.07
    assert rows[0]["terminal_growth"] == 0.02
    assert rows[0]["required_fcf"] == pytest.approx(5_040_464_763_289.6)
    assert rows[2]["required_fcf"] == pytest.approx(7_056_650_668_605.44)


def test_build_required_fcf_table_marks_invalid_spreads_as_none():
    rows = build_required_fcf_table(
        enterprise_value=100,
        current_fcf=10,
        wacc_values=[0.03],
        terminal_growth_values=[0.04],
    )

    assert rows == [
        {
            "wacc": 0.03,
            "terminal_growth": 0.04,
            "required_fcf": None,
            "current_fcf_multiple": None,
        }
    ]


def test_build_required_fcf_matrix_returns_wacc_rows_and_growth_columns():
    rows = build_required_fcf_matrix(
        enterprise_value=100_809_295_265_792,
        current_fcf=243_767_338_650,
        wacc_values=[0.07, 0.09],
        terminal_growth_values=[0.02, 0.03],
    )

    assert rows[0]["wacc"] == 0.07
    assert rows[0][0.02] == pytest.approx(5_040_464_763_289.6)
    assert rows[1][0.03] == pytest.approx(6_048_557_715_947.52)


def test_build_required_fcf_matrix_can_show_current_fcf_multiples():
    rows = build_required_fcf_matrix(
        enterprise_value=100_809_295_265_792,
        current_fcf=243_767_338_650,
        wacc_values=[0.09],
        terminal_growth_values=[0.03],
        metric="current_fcf_multiple",
    )

    assert rows[0][0.03] == pytest.approx(24.8128307486)


def test_build_required_fcf_matrix_rejects_unknown_metric():
    with pytest.raises(ValueError, match="metric must be"):
        build_required_fcf_matrix(100, 10, [0.09], [0.03], metric="value")


def test_calc_normalized_fcf_from_revenue_margin_tax_and_conversion():
    assert calc_normalized_fcf(
        revenue=12_836_400_000_000,
        operating_margin=0.11,
        tax_rate=0.183,
        fcf_conversion=0.70,
    ) == pytest.approx(807_525_087_600)
