from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from valuation_app.models import MetricObservation


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_metric_observations(path: Path) -> list[MetricObservation]:
    rows = load_json(path)
    return [MetricObservation.model_validate(row) for row in rows]


def load_market_data(path: Path) -> dict[str, Any]:
    data = load_json(path)
    required = {"ticker", "company_name", "valuation_date", "market_cap", "price"}
    missing = sorted(required - set(data.keys()))
    if missing:
        raise ValueError(f"Missing market data fields: {', '.join(missing)}")
    return data
