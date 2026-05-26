from __future__ import annotations

from valuation_app.calculations import calc_required_fcf
from valuation_app.reverse_dcf import calc_normalized_fcf


def calc_implied_ev(
    fcf: float | int,
    wacc: float,
    terminal_growth: float,
) -> float | None:
    """Single-stage perpetuity implied enterprise value: EV = FCF / (WACC - g)."""
    if wacc <= terminal_growth:
        return None
    return fcf / (wacc - terminal_growth)


def calc_ev_gap(implied_ev: float | None, current_ev: float | int) -> float | None:
    """Gap between implied EV and current EV as a ratio: (implied - current) / current."""
    if implied_ev is None or current_ev == 0:
        return None
    return (implied_ev - current_ev) / current_ev


def _normalized_fcf_from_params(
    revenue: float | int,
    operating_margin: float,
    tax_rate: float,
    fcf_conversion: float,
) -> float:
    return calc_normalized_fcf(revenue, operating_margin, tax_rate, fcf_conversion)


def build_wacc_growth_sensitivity(
    base_revenue: float | int,
    operating_margin: float,
    tax_rate: float,
    fcf_conversion: float,
    wacc_values: list[float],
    growth_values: list[float],
    current_ev: float | int,
    metric: str = "implied_ev",
) -> list[dict[float | str, float | None]]:
    """Build WACC × terminal-growth sensitivity matrix.

    metric: 'implied_ev' or 'ev_gap'.
    Returns rows keyed by WACC with growth values as columns.
    """
    if metric not in {"implied_ev", "ev_gap"}:
        raise ValueError("metric must be 'implied_ev' or 'ev_gap'.")

    fcf = _normalized_fcf_from_params(base_revenue, operating_margin, tax_rate, fcf_conversion)
    rows: list[dict[float | str, float | None]] = []
    for wacc in wacc_values:
        row: dict[float | str, float | None] = {"wacc": wacc}
        for g in growth_values:
            implied = calc_implied_ev(fcf, wacc, g)
            if metric == "implied_ev":
                row[g] = implied
            else:
                row[g] = calc_ev_gap(implied, current_ev)
        rows.append(row)
    return rows


def build_margin_wacc_sensitivity(
    base_revenue: float | int,
    tax_rate: float,
    fcf_conversion: float,
    margin_values: list[float],
    wacc_values: list[float],
    terminal_growth: float,
    current_ev: float | int,
    metric: str = "ev_gap",
) -> list[dict[float | str, float | None]]:
    """Build operating-margin × WACC sensitivity matrix.

    Returns rows keyed by margin with WACC values as columns.
    """
    if metric not in {"implied_ev", "ev_gap"}:
        raise ValueError("metric must be 'implied_ev' or 'ev_gap'.")

    rows: list[dict[float | str, float | None]] = []
    for margin in margin_values:
        row: dict[float | str, float | None] = {"margin": margin}
        fcf = _normalized_fcf_from_params(base_revenue, margin, tax_rate, fcf_conversion)
        for wacc in wacc_values:
            implied = calc_implied_ev(fcf, wacc, terminal_growth)
            if metric == "implied_ev":
                row[wacc] = implied
            else:
                row[wacc] = calc_ev_gap(implied, current_ev)
        rows.append(row)
    return rows


def build_scenario_table(
    base_revenue: float | int,
    scenarios: list[dict[str, float | str]],
    tax_rate: float,
    fcf_conversion: float,
    current_ev: float | int,
) -> list[dict[str, float | str | None]]:
    """Build bear / base / bull scenario table.

    Each scenario dict must have: name, revenue_growth, operating_margin, wacc, terminal_growth.
    Returns list of dicts with scenario results.
    """
    results: list[dict[str, float | str | None]] = []
    for scenario in scenarios:
        revenue = base_revenue * (1.0 + float(scenario["revenue_growth"]))
        margin = float(scenario["operating_margin"])
        wacc = float(scenario["wacc"])
        g = float(scenario["terminal_growth"])

        fcf = _normalized_fcf_from_params(revenue, margin, tax_rate, fcf_conversion)
        implied = calc_implied_ev(fcf, wacc, g)
        gap = calc_ev_gap(implied, current_ev)

        results.append(
            {
                "시나리오": scenario["name"],
                "매출 성장률": scenario["revenue_growth"],
                "영업이익률": scenario["operating_margin"],
                "WACC": scenario["wacc"],
                "영구성장률": scenario["terminal_growth"],
                "정상화 FCF": fcf,
                "추정 EV": implied,
                "현재 EV 대비 괴리율": gap,
            }
        )
    return results


def rank_value_drivers(
    base_revenue: float | int,
    base_margin: float,
    base_tax_rate: float,
    base_fcf_conversion: float,
    base_wacc: float,
    base_terminal_growth: float,
    current_ev: float | int,
    delta: float = 0.01,
) -> list[dict[str, float | str | None]]:
    """Rank which input variable moves implied EV the most.

    Applies +delta to each variable independently and measures EV change.
    Returns list sorted by absolute EV impact descending.
    """
    base_fcf = _normalized_fcf_from_params(base_revenue, base_margin, base_tax_rate, base_fcf_conversion)
    base_ev = calc_implied_ev(base_fcf, base_wacc, base_terminal_growth)

    drivers: list[dict[str, float | str | None]] = []

    # Revenue growth +delta as fraction of base revenue
    shocked_revenue = base_revenue * (1.0 + delta)
    fcf_revenue = _normalized_fcf_from_params(shocked_revenue, base_margin, base_tax_rate, base_fcf_conversion)
    ev_revenue = calc_implied_ev(fcf_revenue, base_wacc, base_terminal_growth)
    drivers.append(
        {
            "변수": "매출 성장률",
            "기준값": 0.0,
            "변동폭": delta,
            "기준 EV": base_ev,
            "변동 EV": ev_revenue,
            "EV 변화": None if base_ev is None or ev_revenue is None else ev_revenue - base_ev,
            "EV 변화율": None if base_ev is None or ev_revenue is None or base_ev == 0 else (ev_revenue - base_ev) / base_ev,
        }
    )

    # Operating margin +delta
    fcf_margin = _normalized_fcf_from_params(base_revenue, base_margin + delta, base_tax_rate, base_fcf_conversion)
    ev_margin = calc_implied_ev(fcf_margin, base_wacc, base_terminal_growth)
    drivers.append(
        {
            "변수": "영업이익률",
            "기준값": base_margin,
            "변동폭": delta,
            "기준 EV": base_ev,
            "변동 EV": ev_margin,
            "EV 변화": None if base_ev is None or ev_margin is None else ev_margin - base_ev,
            "EV 변화율": None if base_ev is None or ev_margin is None or base_ev == 0 else (ev_margin - base_ev) / base_ev,
        }
    )

    # WACC +delta (higher WACC → lower EV, so we show absolute impact)
    ev_wacc = calc_implied_ev(base_fcf, base_wacc + delta, base_terminal_growth)
    drivers.append(
        {
            "변수": "WACC",
            "기준값": base_wacc,
            "변동폭": delta,
            "기준 EV": base_ev,
            "변동 EV": ev_wacc,
            "EV 변화": None if base_ev is None or ev_wacc is None else ev_wacc - base_ev,
            "EV 변화율": None if base_ev is None or ev_wacc is None or base_ev == 0 else (ev_wacc - base_ev) / base_ev,
        }
    )

    # Terminal growth +delta
    ev_growth = calc_implied_ev(base_fcf, base_wacc, base_terminal_growth + delta)
    drivers.append(
        {
            "변수": "영구성장률",
            "기준값": base_terminal_growth,
            "변동폭": delta,
            "기준 EV": base_ev,
            "변동 EV": ev_growth,
            "EV 변화": None if base_ev is None or ev_growth is None else ev_growth - base_ev,
            "EV 변화율": None if base_ev is None or ev_growth is None or base_ev == 0 else (ev_growth - base_ev) / base_ev,
        }
    )

    # FCF conversion +delta
    fcf_conv = _normalized_fcf_from_params(base_revenue, base_margin, base_tax_rate, base_fcf_conversion + delta)
    ev_conv = calc_implied_ev(fcf_conv, base_wacc, base_terminal_growth)
    drivers.append(
        {
            "변수": "FCF 전환율",
            "기준값": base_fcf_conversion,
            "변동폭": delta,
            "기준 EV": base_ev,
            "변동 EV": ev_conv,
            "EV 변화": None if base_ev is None or ev_conv is None else ev_conv - base_ev,
            "EV 변화율": None if base_ev is None or ev_conv is None or base_ev == 0 else (ev_conv - base_ev) / base_ev,
        }
    )

    # Sort by absolute EV change descending
    drivers.sort(key=lambda d: abs(d["EV 변화"]) if d["EV 변화"] is not None else 0, reverse=True)
    return drivers


def build_risk_metric_explanations() -> list[dict[str, str]]:
    """Beginner-friendly explanation of risk/downside metrics."""
    return [
        {
            "지표": "추정 EV",
            "무슨 뜻인가": "해당 가정 조합에서 단일 단계 영구가치 모형이 계산하는 기업 전체 가치",
            "어떻게 읽나": "현재 EV보다 낮으면 해당 시나리오에서는 현재 주가가 비싸다는 뜻",
        },
        {
            "지표": "괴리율",
            "무슨 뜻인가": "(추정 EV - 현재 EV) / 현재 EV",
            "어떻게 읽나": "양수이면 현재 가격 대비 저평가, 음수이면 고평가 방향. 단 모형 가정에 강하게 의존",
        },
        {
            "지표": "가치 동인 순위",
            "무슨 뜻인가": "각 변수를 1%p 움직였을 때 추정 EV가 얼마나 변하는지 비교",
            "어떻게 읽나": "순위가 높을수록 그 변수가 빗나갈 때 가격 영향이 크다는 뜻",
        },
        {
            "지표": "베어/베이스/불",
            "무슨 뜻인가": "비관적/중립적/낙관적 가정 세트를 각각 적용한 시나리오",
            "어떻게 읽나": "세 시나리오의 추정 EV 범위가 넓을수록 가격 불확실성이 크다는 뜻",
        },
    ]
