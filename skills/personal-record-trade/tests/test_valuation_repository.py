from pathlib import Path

from valuation_app.repository import load_market_data, load_metric_observations


ROOT = Path(__file__).resolve().parents[1]


def test_load_metric_observations_from_seed_data():
    observations = load_metric_observations(ROOT / "data/valuation/009150/normalized/metrics.json")
    keys = {obs.metric_key for obs in observations}

    assert "revenue" in keys
    assert "net_income" in keys
    assert "eps" in keys
    assert "op_cashflow" in keys
    assert "latest_quarter_operating_income" in keys
    assert len(observations) >= 10


def test_load_market_data_from_seed_data():
    market = load_market_data(ROOT / "data/valuation/009150/normalized/market.json")

    assert market["ticker"] == "009150"
    assert market["market_cap"] == 101_233_310_302_208
    assert market["market_data_as_of"] == "2026-05-22"
