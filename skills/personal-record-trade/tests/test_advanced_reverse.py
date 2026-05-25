from valuation_app.advanced_reverse import (
    calc_implied_expected_return,
    calc_implied_growth_from_peg,
    calc_implied_market_share,
    decompose_expected_return,
)


def test_calc_implied_expected_return_normal():
    # EV = 10조, FCF = 5천억 (Yield = 5%), Growth = 3% -> Return = 8%
    assert calc_implied_expected_return(10000.0, 500.0, 0.03) == 0.08


def test_calc_implied_expected_return_edge_cases():
    assert calc_implied_expected_return(0, 500.0, 0.03) is None
    assert calc_implied_expected_return(-1000, 500.0, 0.03) is None
    # FCF가 음수일 때도 계산 자체는 되어야 함 (음의 기대수익률)
    import pytest
    assert calc_implied_expected_return(10000.0, -500.0, 0.03) == pytest.approx(-0.02)


def test_calc_implied_growth_from_peg_normal():
    # PER = 20, PEG = 1.0 => Growth = 20%
    assert calc_implied_growth_from_peg(20.0, 1.0) == 0.20
    # PER = 15, PEG = 1.5 => Growth = 10%
    assert calc_implied_growth_from_peg(15.0, 1.5) == 0.10


def test_calc_implied_growth_from_peg_edge_cases():
    assert calc_implied_growth_from_peg(0, 1.0) is None
    assert calc_implied_growth_from_peg(20.0, 0) is None
    assert calc_implied_growth_from_peg(-5, 1.0) is None


def test_calc_implied_market_share_normal():
    # Required Revenue = 15조, TAM = 50조 => Share = 30%
    assert calc_implied_market_share(15.0, 50.0) == 0.30


def test_calc_implied_market_share_edge_cases():
    assert calc_implied_market_share(-1, 50.0) is None
    assert calc_implied_market_share(15.0, 0) is None
    assert calc_implied_market_share(15.0, -10.0) is None


def test_decompose_expected_return():
    res = decompose_expected_return(0.02, 0.08, 0.05)
    assert res["dividend_yield"] == 0.02
    assert res["earnings_growth"] == 0.08
    assert res["multiple_expansion"] == 0.05
    import pytest
    assert res["total_expected_return"] == pytest.approx(0.15)
