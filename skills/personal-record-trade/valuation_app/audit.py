from __future__ import annotations

from valuation_app.calculations import (
    calc_enterprise_value,
    calc_fcf,
    calc_invested_capital,
    calc_net_debt,
    calc_nopat,
    calc_roic,
)
from valuation_app.models import AuditCheck, MetricObservation, ValuationInputSet


def _observation_map(observations: list[MetricObservation]) -> dict[str, MetricObservation]:
    return {obs.metric_key: obs for obs in observations}


def _value(metrics: dict[str, MetricObservation], key: str) -> float | int | None:
    obs = metrics.get(key)
    return None if obs is None else obs.value


def _status(expected: float | int | None, actual: float | int | None, tolerance: float) -> str:
    if expected is None or actual is None:
        return "fail"
    return "pass" if abs(expected - actual) <= tolerance else "warning"


def _calculated_observation(
    metric_key: str,
    label: str,
    value: float | int | None,
    period: str,
    note: str,
) -> MetricObservation:
    return MetricObservation(
        metric_key=metric_key,
        label=label,
        value=value,
        unit="ratio" if metric_key == "roic" else "KRW",
        period=period,
        source_method="calculated",
        confidence=1.0 if value is not None else 0.0,
        note=note,
    )


def build_input_set(observations: list[MetricObservation], market: dict) -> ValuationInputSet:
    metrics = _observation_map(observations)
    inputs = {key: obs.value for key, obs in metrics.items()}
    inputs["price"] = float(market["price"])
    inputs["shares_outstanding"] = float(market["shares_outstanding"])
    inputs["market_cap"] = float(market["market_cap"])
    observation_keys = {key: key for key in inputs.keys()}

    return ValuationInputSet(
        ticker=market["ticker"],
        company_name=market["company_name"],
        valuation_date=market["valuation_date"],
        inputs=inputs,
        observation_keys=observation_keys,
    )


def run_audit(
    observations: list[MetricObservation],
    market: dict,
) -> tuple[ValuationInputSet, list[AuditCheck], list[MetricObservation]]:
    metrics = _observation_map(observations)
    checks: list[AuditCheck] = []
    derived: list[MetricObservation] = []

    op_cashflow = _value(metrics, "op_cashflow")
    capex = _value(metrics, "capex")
    reported_fcf = _value(metrics, "fcf")
    calculated_fcf = None if op_cashflow is None or capex is None else calc_fcf(op_cashflow, capex)
    checks.append(
        AuditCheck(
            check_key="fcf_reconciliation",
            label="FCF 검산",
            formula="FCF = 영업활동현금흐름 - CAPEX",
            expected_value=calculated_fcf,
            actual_value=reported_fcf,
            tolerance=1.0,
            status=_status(calculated_fcf, reported_fcf, 1.0),
            inputs=["op_cashflow", "capex", "fcf"],
            explanation="CAPEX는 양수 현금유출로 정규화한 뒤 영업현금흐름에서 차감합니다.",
        )
    )

    short_debt = _value(metrics, "short_debt")
    long_debt = _value(metrics, "long_debt")
    cash = _value(metrics, "cash")
    reported_net_debt = _value(metrics, "net_debt")
    calculated_net_debt = (
        None
        if short_debt is None or long_debt is None or cash is None
        else calc_net_debt(short_debt, long_debt, cash)
    )
    checks.append(
        AuditCheck(
            check_key="net_debt_reconciliation",
            label="순부채 검산",
            formula="순부채 = 단기차입금 + 장기차입금 - 현금",
            expected_value=calculated_net_debt,
            actual_value=reported_net_debt,
            tolerance=1.0,
            status=_status(calculated_net_debt, reported_net_debt, 1.0),
            inputs=["short_debt", "long_debt", "cash", "net_debt"],
            explanation="순현금 기업이면 순부채는 음수가 됩니다.",
        )
    )

    enterprise_value = None
    if calculated_net_debt is not None:
        enterprise_value = calc_enterprise_value(float(market["market_cap"]), calculated_net_debt)
        derived.append(
            _calculated_observation(
                "enterprise_value",
                "EV",
                enterprise_value,
                market["valuation_date"],
                "EV = 시가총액 + 순부채",
            )
        )

    reported_ev = market.get("reported_enterprise_value")
    ev_status = "fail"
    ev_explanation = "EV 계산값을 만들 수 없습니다."
    if enterprise_value is not None and reported_ev is not None:
        gap = abs(enterprise_value - float(reported_ev))
        ev_status = "pass" if gap <= 100_000_000_000 else "warning"
        ev_explanation = "시장 데이터 제공자의 EV와 직접 계산한 EV가 다르면 구성 항목 차이를 확인합니다."
    checks.append(
        AuditCheck(
            check_key="reported_ev_gap",
            label="EV 제공값 비교",
            formula="EV = 시가총액 + 순부채",
            expected_value=enterprise_value,
            actual_value=float(reported_ev) if reported_ev is not None else None,
            tolerance=100_000_000_000.0,
            status=ev_status,
            inputs=["market_cap", "net_debt", "reported_enterprise_value"],
            explanation=ev_explanation,
        )
    )

    operating_income = _value(metrics, "operating_income")
    tax_rate = _value(metrics, "tax_rate")
    nopat = None if operating_income is None or tax_rate is None else calc_nopat(operating_income, tax_rate)
    derived.append(_calculated_observation("nopat", "NOPAT", nopat, "2025A", "NOPAT = 영업이익 × (1 - 세율)"))

    total_equity = _value(metrics, "total_equity")
    invested_capital = (
        None
        if total_equity is None or calculated_net_debt is None
        else calc_invested_capital(total_equity, calculated_net_debt)
    )
    derived.append(
        _calculated_observation(
            "invested_capital",
            "투하자본",
            invested_capital,
            "2025A",
            "투하자본 = 자본총계 + 순부채",
        )
    )

    roic = None if nopat is None or invested_capital is None else calc_roic(nopat, invested_capital)
    derived.append(_calculated_observation("roic", "ROIC", roic, "2025A", "ROIC = NOPAT / 투하자본"))

    input_set = build_input_set(observations + derived, market)
    return input_set, checks, derived
