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
    grouped: dict[str, list[MetricObservation]] = {}
    for obs in observations:
        grouped.setdefault(obs.metric_key, []).append(obs)
        
    result: dict[str, MetricObservation] = {}
    for key, obs_list in grouped.items():
        annual_obs = []
        for obs in obs_list:
            if obs.period and obs.period.endswith("A"):
                try:
                    year = int(obs.period[:-1])
                    annual_obs.append((year, obs))
                except ValueError:
                    continue
        
        if annual_obs:
            annual_obs.sort(key=lambda x: x[0], reverse=True)
            result[key] = annual_obs[0][1]
        else:
            result[key] = obs_list[-1]
            
    return result



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

    # 1. 영업마진 일관성 검증 (Operating Margin Consistency)
    revenue = _value(metrics, "revenue")
    op_margin_status = "fail"
    op_margin_val = None
    if revenue is not None and operating_income is not None and revenue != 0:
        op_margin_val = operating_income / revenue
        if abs(operating_income) > revenue:
            op_margin_status = "fail"
        elif operating_income < 0:
            op_margin_status = "warning"  # 영업적자 상태 경고
        else:
            op_margin_status = "pass"
    checks.append(
        AuditCheck(
            check_key="operating_margin_consistency",
            label="영업마진 일관성",
            formula="영업마진 = 영업이익 / 매출액 (절대값 <= 1.0 및 영업적자 여부 검증)",
            expected_value=op_margin_val,
            actual_value=op_margin_val,
            tolerance=0.0,
            status=op_margin_status,
            inputs=["operating_income", "revenue"],
            explanation="영업이익률이 100%를 초과할 수 없으며, 영업이익이 마이너스이면 경고가 발생합니다.",
        )
    )

    # 2. FCF vs 영업현금흐름 검증 (FCF vs Operating Cash Flow)
    fcf_vs_op_status = "fail"
    if op_cashflow is not None and capex is not None and reported_fcf is not None:
        if capex < 0 or reported_fcf > op_cashflow:
            fcf_vs_op_status = "fail"
        else:
            fcf_vs_op_status = "pass"
    checks.append(
        AuditCheck(
            check_key="fcf_vs_op_cashflow",
            label="FCF 영업현금흐름 비교",
            formula="FCF <= 영업현금흐름 (CAPEX >= 0 가정)",
            expected_value=op_cashflow - capex if op_cashflow is not None and capex is not None else None,
            actual_value=reported_fcf,
            tolerance=1.0,
            status=fcf_vs_op_status,
            inputs=["fcf", "op_cashflow", "capex"],
            explanation="CAPEX는 양수 지출이어야 하므로 FCF는 항상 영업현금흐름보다 작거나 같아야 합니다.",
        )
    )

    # 3. 매출액 vs 영업이익 절대값 비교 검증 (Revenue vs Operating Income)
    rev_vs_op_status = "fail"
    if revenue is not None and operating_income is not None:
        if revenue < abs(operating_income):
            rev_vs_op_status = "fail"
        else:
            rev_vs_op_status = "pass"
    checks.append(
        AuditCheck(
            check_key="revenue_vs_operating_income",
            label="매출액 영업이익 비교",
            formula="매출액 >= |영업이익|",
            expected_value=revenue,
            actual_value=abs(operating_income) if operating_income is not None else None,
            tolerance=0.0,
            status=rev_vs_op_status,
            inputs=["revenue", "operating_income"],
            explanation="영업이익의 절대값이 매출액보다 큰 경우 데이터 매핑에 치명적인 오류가 있음을 뜻합니다.",
        )
    )

    # 4. 통화 단위 정합성 검증 (Currency Unit Consistency)
    currency_val = market.get("currency", "원")
    is_usd_stock = currency_val in ["USD", "달러"]
    unit_status = "pass"
    mismatched_metrics = []
    
    for obs in observations:
        if obs.metric_key in ["revenue", "operating_income", "net_income", "cash", "total_equity"]:
            obs_unit = obs.unit or ""
            if is_usd_stock and obs_unit != "USD":
                unit_status = "fail"
                mismatched_metrics.append(f"{obs.metric_key}({obs_unit})")
            elif not is_usd_stock and obs_unit != "KRW" and obs_unit != "원":
                unit_status = "fail"
                mismatched_metrics.append(f"{obs.metric_key}({obs_unit})")
                
    explanation_unit = "시장 데이터의 통화 단위와 재무 데이터의 화폐 단위가 일치합니다."
    if unit_status == "fail":
        explanation_unit = f"통화 단위 불일치 검출: {', '.join(mismatched_metrics)}. 달러 주식은 USD, 한국 주식은 KRW 단위여야 합니다."
        
    checks.append(
        AuditCheck(
            check_key="currency_unit_consistency",
            label="통화 단위 정합성",
            formula="주식 통화 == 재무제표 단위",
            expected_value=None,
            actual_value=None,
            tolerance=0.0,
            status=unit_status,
            inputs=["currency"],
            explanation=explanation_unit,
        )
    )

    # 5. 현재 PER 이상치 검증 (Current PER Anomaly)
    current_price = market.get("price")
    eps_val = _value(metrics, "eps")
    per_status = "pass"
    per_calc = None
    explanation_per = "현재 PER이 정상 범위(0 ~ 300배) 내에 있습니다."
    
    if current_price is not None and eps_val is not None and eps_val != 0:
        per_calc = float(current_price) / float(eps_val)
        if per_calc < 0:
            per_status = "warning"
            explanation_per = f"현재 계산된 PER이 음수({per_calc:.2f}배)입니다. 기업이 현재 적자 상태인지 확인이 필요합니다."
        elif per_calc > 300:
            per_status = "warning"
            explanation_per = f"현재 계산된 PER이 초고배율({per_calc:.2f}배)입니다. 초성장주이거나 EPS의 통화 단위 매핑 오류(원화/달러 혼용)인지 확인하십시오."
            
    checks.append(
        AuditCheck(
            check_key="current_per_anomaly",
            label="현재 PER 이상치 검증",
            formula="PER = 현재가 / 최신 EPS",
            expected_value=per_calc,
            actual_value=per_calc,
            tolerance=0.0,
            status=per_status,
            inputs=["price", "eps"],
            explanation=explanation_per,
        )
    )

    input_set = build_input_set(observations + derived, market)
    return input_set, checks, derived
