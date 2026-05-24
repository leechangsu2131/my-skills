import pytest

from valuation_app.relative_valuation import (
    build_relative_metric_explanations,
    calc_ev_to_nopat,
    calc_ev_to_sales,
    calc_implied_nopat_margin_from_ev_sales,
    calc_implied_operating_margin_from_ev_sales,
    calc_implied_roe_from_pb,
    calc_price_to_book,
)


def test_calc_price_to_book():
    assert calc_price_to_book(101_233_310_302_208, 9_541_761_553_950) == pytest.approx(10.6094990668)


def test_calc_price_to_book_returns_none_when_equity_is_not_positive():
    assert calc_price_to_book(100, 0) is None
    assert calc_price_to_book(100, -1) is None


def test_calc_ev_to_sales_and_ev_to_nopat():
    assert calc_ev_to_sales(100_809_295_265_792, 11_314_459_238_100) == pytest.approx(8.9097758138)
    assert calc_ev_to_nopat(100_809_295_265_792, 746_191_572_614) == pytest.approx(135.0984103354)


def test_calc_multiples_return_none_when_denominator_is_not_positive():
    assert calc_ev_to_sales(100, 0) is None
    assert calc_ev_to_nopat(100, -1) is None


def test_calc_implied_roe_from_pb():
    implied_roe = calc_implied_roe_from_pb(price_to_book=10.6094990668, required_return=0.10, growth_rate=0.03)

    assert implied_roe == pytest.approx(0.7726649347)


def test_calc_implied_roe_from_pb_returns_none_when_formula_invalid():
    assert calc_implied_roe_from_pb(None, 0.10, 0.03) is None
    assert calc_implied_roe_from_pb(1.5, 0.03, 0.03) is None


def test_calc_implied_margin_from_ev_sales():
    nopat_margin = calc_implied_nopat_margin_from_ev_sales(
        ev_sales=8.9097758138,
        wacc=0.09,
        growth_rate=0.03,
        roic=0.25,
    )
    operating_margin = calc_implied_operating_margin_from_ev_sales(
        ev_sales=8.9097758138,
        wacc=0.09,
        growth_rate=0.03,
        roic=0.25,
        tax_rate=0.183,
    )

    assert nopat_margin == pytest.approx(0.5897909850)
    assert operating_margin == pytest.approx(0.7218983905)


def test_calc_implied_margin_returns_none_when_formula_invalid():
    assert calc_implied_nopat_margin_from_ev_sales(None, 0.09, 0.03, 0.25) is None
    assert calc_implied_nopat_margin_from_ev_sales(5, 0.03, 0.03, 0.25) is None
    assert calc_implied_nopat_margin_from_ev_sales(5, 0.09, 0.03, 0.03) is None
    assert calc_implied_operating_margin_from_ev_sales(5, 0.09, 0.03, 0.25, 1.0) is None


def test_build_relative_metric_explanations_are_beginner_friendly():
    rows = build_relative_metric_explanations()

    assert rows[0]["지표"] == "P/E"
    assert "순이익" in rows[0]["무슨 뜻인가"]
    assert any(row["지표"] == "P/B" and "내포 ROE" in row["어떻게 읽나"] for row in rows)
    assert any(row["지표"] == "EV/Sales" and "필요 마진" in row["어떻게 읽나"] for row in rows)
