from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from valuation_app.audit import run_audit
from valuation_app.calculations import calc_required_fcf
from valuation_app.cap_duration import (
    build_cap_duration_table,
    build_cap_metric_explanations,
    calc_annual_economic_profit_from_roic,
    calc_discounted_cap_years,
    calc_simple_payback_years,
)
from valuation_app.formatting import format_krw, format_ratio, source_label, status_label
from valuation_app.margin_scenario import (
    build_margin_scenario_matrix,
    build_required_margin_table,
    calc_required_revenue,
)
from valuation_app.models import AuditCheck, MetricObservation, ValuationInputSet
from valuation_app.repository import load_market_data, load_metric_observations
from valuation_app.relative_valuation import (
    build_relative_metric_explanations,
    calc_ev_to_nopat,
    calc_ev_to_sales,
    calc_implied_nopat_margin_from_ev_sales,
    calc_implied_operating_margin_from_ev_sales,
    calc_implied_roe_from_pb,
    calc_pe_from_eps,
    calc_price_to_earnings,
    calc_price_to_book,
)
from valuation_app.reverse_dcf import build_required_fcf_matrix, calc_normalized_fcf, required_fcf_multiple
from valuation_app.roic_reinvestment import (
    build_reinvestment_matrix,
    build_roic_metric_explanations,
    calc_economic_profit,
    calc_ev_nopat_multiple,
    calc_implied_future_roic_from_invested_capital,
    calc_implied_roic_from_value_driver,
    calc_max_ev_nopat_multiple,
    calc_reinvestment_rate,
)
from valuation_app.value_attribution import (
    build_value_attribution_table,
    calc_future_expectation_ratio,
    calc_future_expectation_value,
    calc_no_growth_value,
)


ROOT = Path(__file__).resolve().parents[1]
METRICS_PATH = ROOT / "data/valuation/009150/normalized/metrics.json"
MARKET_PATH = ROOT / "data/valuation/009150/normalized/market.json"


def _display_value(obs: MetricObservation) -> str:
    if obs.unit == "ratio":
        return format_ratio(obs.value)
    if obs.unit == "KRW/share":
        return _format_price(obs.value)
    return format_krw(obs.value)


def _display_original_value(obs: MetricObservation) -> str:
    if obs.original_amount is None:
        return "-"
    if obs.unit == "ratio":
        return format_ratio(obs.original_amount)
    if obs.unit == "KRW/share":
        return _format_price(obs.original_amount)
    return format_krw(obs.original_amount)


def _format_price(value: float | int | None) -> str:
    if value is None:
        return "-"
    return f"{value:,.0f}원"


def _check_rows(checks: list[AuditCheck]) -> list[dict[str, str]]:
    rows = []
    for check in checks:
        rows.append(
            {
                "검산": check.label,
                "상태": status_label(check.status),
                "공식": check.formula,
                "계산값": format_krw(check.expected_value),
                "비교값": format_krw(check.actual_value),
                "설명": check.explanation,
            }
        )
    return rows


def _format_multiple(value: float | int | None) -> str:
    if value is None:
        return "-"
    return f"{value:.1f}배"


def _observation_rows(observations: list[MetricObservation]) -> list[dict[str, str]]:
    rows = []
    for obs in observations:
        rows.append(
            {
                "입력값": obs.label,
                "값": _display_value(obs),
                "기간": obs.period,
                "출처": source_label(obs.source_method),
                "보고서": obs.report_code or "-",
                "원문 계정": obs.original_account_name or "-",
                "신뢰도": format_ratio(obs.confidence),
                "메모": obs.note,
            }
        )
    return rows


def _reverse_dcf_matrix(
    enterprise_value: float | int,
    current_fcf: float | int | None,
    wacc_values: list[float],
    terminal_growth_values: list[float],
    metric: str,
) -> pd.DataFrame:
    rows = build_required_fcf_matrix(
        enterprise_value=enterprise_value,
        current_fcf=current_fcf,
        wacc_values=wacc_values,
        terminal_growth_values=terminal_growth_values,
        metric=metric,
    )
    matrix = pd.DataFrame(rows).set_index("wacc")
    matrix.index = [format_ratio(value) for value in matrix.index]
    matrix.columns = [format_ratio(value) for value in matrix.columns]
    matrix.index.name = "WACC \\ g"
    return matrix


def _value_attribution_rows(rows: list[dict[str, float | None]]) -> list[dict[str, str]]:
    formatted = []
    for row in rows:
        formatted.append(
            {
                "WACC": format_ratio(row["wacc"]),
                "현재 수익력 가치": format_krw(row["no_growth_value"]),
                "미래 기대 가치": format_krw(row["future_expectation_value"]),
                "미래 기대 비중": format_ratio(row["future_expectation_ratio"]),
            }
        )
    return formatted


def _required_margin_rows(rows: list[dict[str, float | None]]) -> list[dict[str, str]]:
    formatted = []
    for row in rows:
        formatted.append(
            {
                "매출 성장률": format_ratio(row["growth_rate"]),
                "시나리오 매출": format_krw(row["scenario_revenue"]),
                "필요 영업이익률": format_ratio(row["required_operating_margin"]),
            }
        )
    return formatted


def _margin_scenario_matrix(
    base_revenue: float | int,
    required_fcf: float | int,
    growth_rates: list[float],
    operating_margins: list[float],
    tax_rate: float,
    fcf_conversion: float,
) -> pd.DataFrame:
    rows = build_margin_scenario_matrix(
        base_revenue=base_revenue,
        required_fcf=required_fcf,
        growth_rates=growth_rates,
        operating_margins=operating_margins,
        tax_rate=tax_rate,
        fcf_conversion=fcf_conversion,
    )
    matrix = pd.DataFrame(rows).set_index("growth_rate")
    matrix.index = [format_ratio(value) for value in matrix.index]
    matrix.columns = [format_ratio(value) for value in matrix.columns]
    matrix.index.name = "매출 성장률 \\ OPM"
    return matrix


def _reinvestment_matrix(growth_rates: list[float], roic_values: list[float]) -> pd.DataFrame:
    rows = build_reinvestment_matrix(growth_rates=growth_rates, roic_values=roic_values)
    matrix = pd.DataFrame(rows).set_index("growth_rate")
    matrix.index = [format_ratio(value) for value in matrix.index]
    matrix.columns = [format_ratio(value) for value in matrix.columns]
    matrix.index.name = "성장률 \\ ROIC"
    return matrix


def _format_sensitivity_cell(value: float | None, unit: str) -> str:
    if value is None or pd.isna(value):
        return "-"
    if unit == "krw_trillion":
        return f"{value / 1_000_000_000_000:.1f}조"
    return f"{value:.1f}배"


def _format_coverage_cell(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "-"
    return format_ratio(value)


def _format_reinvestment_cell(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "-"
    return format_ratio(value)


def _format_roic_solution(value: float | None) -> str:
    if value is None:
        return "해 없음"
    return format_ratio(value)


def _format_years(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "불가능"
    return f"{value:.1f}년"


def _cap_duration_rows(rows: list[dict[float | str, float | None]], periods: list[int]) -> list[dict[str, str]]:
    formatted: list[dict[str, str]] = []
    for row in rows:
        item = {
            "ROIC": format_ratio(row["roic"]),
            "연간 경제적 이익": format_krw(row["annual_economic_profit"]),
            "단순 CAP": _format_years(row["simple_payback_years"]),
            "할인 CAP": _format_years(row["discounted_cap_years"]),
        }
        for years in periods:
            item[f"{years}년 PV"] = format_krw(row[years])
        formatted.append(item)
    return formatted


def render_source_panel(obs: MetricObservation) -> None:
    st.markdown(f"#### {obs.label}")
    st.write(f"값: **{_display_value(obs)}**")
    st.write(f"출처: **{source_label(obs.source_method)}**")
    st.write(f"기간: `{obs.period}`")
    st.write(f"보고서 코드: `{obs.report_code or '-'}`")
    st.write(f"재무제표: `{obs.statement_name or '-'}`")
    st.write(f"원문 계정명: `{obs.original_account_name or '-'}`")
    st.write(f"원문 금액: `{_display_original_value(obs)}`")
    st.write(f"신뢰도: `{format_ratio(obs.confidence)}`")
    st.info(obs.note or "메모 없음")


def render_reverse_dcf_tab(input_set: ValuationInputSet) -> None:
    enterprise_value = input_set.inputs.get("enterprise_value")
    current_fcf = input_set.inputs.get("fcf")
    annual_revenue = input_set.inputs.get("revenue")
    tax_rate = input_set.inputs.get("tax_rate") or 0.183
    latest_quarter_revenue = input_set.inputs.get("latest_quarter_revenue")
    latest_quarter_operating_income = input_set.inputs.get("latest_quarter_operating_income")

    st.markdown("현재 EV를 정당화하려면 다음 1년 FCF가 어느 정도여야 하는지 역산합니다.")
    st.code("필요 FCF1 = EV × (WACC - 영구성장률)", language="text")

    if enterprise_value is None or current_fcf is None:
        st.error("Reverse DCF에 필요한 EV 또는 FCF가 없습니다. 먼저 데이터 검산을 확인하세요.")
        return

    left, right = st.columns(2)
    wacc = left.slider("WACC", min_value=5.0, max_value=13.0, value=9.0, step=0.5) / 100.0
    terminal_growth = right.slider("영구성장률 g", min_value=0.0, max_value=5.0, value=3.0, step=0.5) / 100.0

    if wacc <= terminal_growth:
        st.warning("WACC는 영구성장률보다 커야 합니다. 차이가 0 이하이면 영구가치 공식이 성립하지 않습니다.")
        return

    required_fcf = calc_required_fcf(float(enterprise_value), wacc, terminal_growth)
    multiple = required_fcf_multiple(required_fcf, current_fcf)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("직접 계산 EV", format_krw(enterprise_value))
    m2.metric("현재 2025 FCF", format_krw(current_fcf))
    m3.metric("필요 FCF1", format_krw(required_fcf))
    m4.metric("현재 FCF 대비", _format_multiple(multiple))

    if multiple is not None and multiple >= 10:
        st.warning(
            "현재 FCF만으로는 가격을 설명하기 어렵습니다. 시장은 훨씬 높은 정상화 FCF, 낮은 할인율, "
            "또는 긴 초과수익 기간을 기대하고 있다는 신호로 읽어야 합니다."
        )
    else:
        st.info("현재 FCF와 필요 FCF의 차이가 작을수록 가격이 현재 현금창출력에 더 많이 기대고 있다는 뜻입니다.")

    st.markdown("#### WACC / 영구성장률 민감도")
    st.caption("행은 WACC, 열은 영구성장률입니다. 전형적인 DCF 민감도 표처럼 볼 수 있게 낮은 요구치는 녹색, 높은 요구치는 붉은색으로 표시합니다.")
    wacc_grid = [0.07, 0.08, 0.09, 0.10, 0.11]
    growth_grid = [0.01, 0.02, 0.03, 0.04]
    required_matrix = _reverse_dcf_matrix(float(enterprise_value), current_fcf, wacc_grid, growth_grid, "required_fcf")
    multiple_matrix = _reverse_dcf_matrix(
        float(enterprise_value), current_fcf, wacc_grid, growth_grid, "current_fcf_multiple"
    )

    s_required, s_multiple = st.tabs(["필요 FCF", "현재 FCF 대비 배수"])
    with s_required:
        st.dataframe(
            required_matrix.style.format(lambda value: _format_sensitivity_cell(value, "krw_trillion")).background_gradient(
                cmap="RdYlGn_r", axis=None
            ),
            use_container_width=True,
        )
    with s_multiple:
        st.dataframe(
            multiple_matrix.style.format(lambda value: _format_sensitivity_cell(value, "multiple")).background_gradient(
                cmap="RdYlGn_r", axis=None
            ),
            use_container_width=True,
        )

    st.markdown("#### 정상화 FCF 사고실험")
    base_options = ["2025 연간 매출", "2026 Q1 run-rate"]
    base_choice = st.radio("매출 기준", base_options, horizontal=True)
    quarter_run_rate = None if latest_quarter_revenue is None else latest_quarter_revenue * 4
    base_revenue = annual_revenue if base_choice == "2025 연간 매출" else quarter_run_rate

    if base_revenue is None:
        st.info("정상화 FCF를 계산할 매출 기준값이 없습니다.")
        return

    latest_margin = 9.0
    if latest_quarter_revenue and latest_quarter_operating_income:
        latest_margin = round(float(latest_quarter_operating_income) / float(latest_quarter_revenue) * 100, 1)

    s1, s2, s3 = st.columns(3)
    op_margin = s1.slider("정상화 영업이익률", min_value=0.0, max_value=40.0, value=latest_margin, step=0.5) / 100.0
    scenario_tax_rate = s2.slider("세율", min_value=0.0, max_value=40.0, value=round(float(tax_rate) * 100, 1), step=0.1) / 100.0
    fcf_conversion = s3.slider("NOPAT → FCF 전환율", min_value=0.0, max_value=120.0, value=70.0, step=5.0) / 100.0

    normalized_fcf = calc_normalized_fcf(base_revenue, op_margin, scenario_tax_rate, fcf_conversion)
    coverage = required_fcf_multiple(normalized_fcf, required_fcf)

    n1, n2, n3 = st.columns(3)
    n1.metric("매출 기준", format_krw(base_revenue))
    n2.metric("정상화 FCF", format_krw(normalized_fcf))
    n3.metric("필요 FCF 충족률", format_ratio(coverage))

    st.caption(
        "정상화 FCF = 매출 × 영업이익률 × (1 - 세율) × FCF 전환율. "
        "이 사고실험은 정답이 아니라 현재 가격이 요구하는 규모감을 몸으로 익히기 위한 장치입니다."
    )
    if op_margin >= 0.25:
        st.warning(
            "영업이익률 25% 이상은 강한 프리미엄/구조적 개선 가정입니다. "
            "불가능하다는 뜻은 아니지만, 과거 실적과 peer margin으로 별도 검증해야 합니다."
        )


def render_value_attribution_tab(input_set: ValuationInputSet) -> None:
    enterprise_value = input_set.inputs.get("enterprise_value")
    nopat = input_set.inputs.get("nopat")
    operating_income = input_set.inputs.get("operating_income")
    tax_rate = input_set.inputs.get("tax_rate")

    st.markdown("현재 EV를 현재 수익력 가치와 미래 기대 가치로 나눠 봅니다.")
    st.code(
        "현재 수익력 가치 = NOPAT / WACC\n미래 기대 가치 = EV - 현재 수익력 가치",
        language="text",
    )

    if enterprise_value is None or nopat is None:
        st.error("Value Attribution에 필요한 EV 또는 NOPAT이 없습니다. 먼저 데이터 검산을 확인하세요.")
        return

    left, right = st.columns([1, 1])
    wacc = left.slider("Value Attribution WACC", min_value=5.0, max_value=13.0, value=9.0, step=0.5) / 100.0
    right.caption("WACC가 낮을수록 같은 NOPAT의 현재 수익력 가치가 커집니다.")

    no_growth_value = calc_no_growth_value(nopat, wacc)
    future_value = calc_future_expectation_value(enterprise_value, no_growth_value)
    future_ratio = calc_future_expectation_ratio(future_value, enterprise_value)
    no_growth_ratio = calc_future_expectation_ratio(no_growth_value, enterprise_value)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("EV", format_krw(enterprise_value))
    m2.metric("NOPAT", format_krw(nopat))
    m3.metric("현재 수익력 가치", format_krw(no_growth_value))
    m4.metric("미래 기대 비중", format_ratio(future_ratio))

    split_df = pd.DataFrame(
        [
            {"구분": "현재 수익력 가치", "비중": no_growth_ratio or 0.0},
            {"구분": "미래 기대 가치", "비중": future_ratio or 0.0},
        ]
    ).set_index("구분")
    st.bar_chart(split_df)

    if future_ratio is not None and future_ratio >= 0.7:
        st.warning(
            "EV의 대부분이 미래 기대 가치입니다. 이는 곧바로 고평가라는 뜻은 아니지만, "
            "성장·마진·ROIC 가정이 실망하면 가격 민감도가 커질 수 있다는 뜻입니다."
        )
    else:
        st.info("현재 수익력 가치가 EV의 큰 부분을 설명할수록 가격은 현재 이익 기반에 더 많이 기대고 있습니다.")

    st.markdown("#### WACC 민감도")
    attribution_rows = build_value_attribution_table(
        enterprise_value=enterprise_value,
        nopat=nopat,
        wacc_values=[0.07, 0.08, 0.09, 0.10, 0.11],
    )
    st.dataframe(_value_attribution_rows(attribution_rows), use_container_width=True, hide_index=True)

    with st.expander("입력값 출처와 계산 흐름"):
        st.markdown(
            f"""
            - 영업이익: `{format_krw(operating_income)}`
            - 세율: `{format_ratio(tax_rate)}`
            - NOPAT: `{format_krw(nopat)}`
            - 직접 계산 EV: `{format_krw(enterprise_value)}`
            - 공식: `NOPAT / WACC`, `EV - 현재 수익력 가치`
            """
        )


def render_margin_scenario_tab(input_set: ValuationInputSet) -> None:
    enterprise_value = input_set.inputs.get("enterprise_value")
    annual_revenue = input_set.inputs.get("revenue")
    tax_rate = input_set.inputs.get("tax_rate") or 0.183
    latest_quarter_revenue = input_set.inputs.get("latest_quarter_revenue")
    latest_quarter_operating_income = input_set.inputs.get("latest_quarter_operating_income")

    st.markdown("필요 FCF를 매출과 영업이익률 조합으로 바꿔 봅니다.")
    st.code("정상화 FCF = 매출 × 영업이익률 × (1 - 세율) × FCF 전환율", language="text")

    if enterprise_value is None or annual_revenue is None:
        st.error("시나리오 분석에 필요한 EV 또는 매출이 없습니다. 먼저 데이터 검산을 확인하세요.")
        return

    c1, c2, c3 = st.columns(3)
    wacc = c1.slider("Scenario WACC", min_value=5.0, max_value=13.0, value=9.0, step=0.5) / 100.0
    terminal_growth = c2.slider("Scenario 영구성장률 g", min_value=0.0, max_value=5.0, value=3.0, step=0.5) / 100.0
    fcf_conversion = c3.slider("Scenario FCF 전환율", min_value=10.0, max_value=120.0, value=70.0, step=5.0) / 100.0

    if wacc <= terminal_growth:
        st.warning("WACC는 영구성장률보다 커야 합니다.")
        return

    required_fcf = calc_required_fcf(float(enterprise_value), wacc, terminal_growth)
    quarter_run_rate = None if latest_quarter_revenue is None else latest_quarter_revenue * 4
    base_options = ["2025 연간 매출"]
    if quarter_run_rate is not None:
        base_options.append("2026 Q1 run-rate")
    base_choice = st.radio("기준 매출", base_options, horizontal=True)
    base_revenue = annual_revenue if base_choice == "2025 연간 매출" else quarter_run_rate

    if base_revenue is None:
        st.info("기준 매출을 계산할 수 없습니다.")
        return

    latest_margin = None
    if latest_quarter_revenue and latest_quarter_operating_income:
        latest_margin = latest_quarter_operating_income / latest_quarter_revenue

    required_margin = build_required_margin_table(
        base_revenue=base_revenue,
        required_fcf=required_fcf,
        growth_rates=[0.0],
        tax_rate=float(tax_rate),
        fcf_conversion=fcf_conversion,
    )[0]["required_operating_margin"]
    revenue_at_25_margin = calc_required_revenue(required_fcf, 0.25, float(tax_rate), fcf_conversion)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("필요 FCF", format_krw(required_fcf))
    m2.metric("기준 매출", format_krw(base_revenue))
    m3.metric("필요 영업이익률", format_ratio(required_margin))
    m4.metric("OPM 25%일 때 필요 매출", format_krw(revenue_at_25_margin))

    if required_margin is not None and required_margin >= 0.4:
        st.warning(
            "필요 영업이익률이 40%를 넘습니다. 이 경우 가격 설명은 단순 마진 개선보다 매출 규모 확대, "
            "재투자 효율, 장기 경쟁우위 기간까지 함께 봐야 합니다."
        )
    elif required_margin is not None and required_margin >= 0.25:
        st.warning("필요 영업이익률이 25% 이상입니다. 프리미엄 제품 믹스와 peer margin으로 별도 검증해야 합니다.")
    else:
        st.info("필요 영업이익률이 산업적으로 가능한 범위인지 과거 실적과 peer margin으로 비교하세요.")

    if latest_margin is not None:
        st.caption(f"참고: 2026 Q1 발표 기준 단순 영업이익률은 약 {format_ratio(latest_margin)}입니다.")

    st.markdown("#### 매출 성장률별 필요 영업이익률")
    required_margin_rows = build_required_margin_table(
        base_revenue=base_revenue,
        required_fcf=required_fcf,
        growth_rates=[0.0, 0.1, 0.2, 0.3, 0.5, 1.0],
        tax_rate=float(tax_rate),
        fcf_conversion=fcf_conversion,
    )
    st.dataframe(_required_margin_rows(required_margin_rows), use_container_width=True, hide_index=True)

    st.markdown("#### 매출 성장률 × 영업이익률 충족률")
    st.caption("각 칸은 해당 조합의 정상화 FCF가 필요 FCF의 몇 %를 채우는지 보여줍니다. 100% 이상이면 현재 선택한 WACC/g 기준을 충족합니다.")
    coverage_matrix = _margin_scenario_matrix(
        base_revenue=base_revenue,
        required_fcf=required_fcf,
        growth_rates=[0.0, 0.1, 0.2, 0.3, 0.5, 1.0],
        operating_margins=[0.08, 0.12, 0.16, 0.20, 0.25, 0.30, 0.40],
        tax_rate=float(tax_rate),
        fcf_conversion=fcf_conversion,
    )
    st.dataframe(
        coverage_matrix.style.format(_format_coverage_cell).background_gradient(cmap="RdYlGn", axis=None),
        use_container_width=True,
    )


def render_roic_reinvestment_tab(input_set: ValuationInputSet) -> None:
    enterprise_value = input_set.inputs.get("enterprise_value")
    operating_income = input_set.inputs.get("operating_income")
    tax_rate = input_set.inputs.get("tax_rate")
    nopat = input_set.inputs.get("nopat")
    total_equity = input_set.inputs.get("total_equity")
    net_debt = input_set.inputs.get("net_debt")
    invested_capital = input_set.inputs.get("invested_capital")
    roic = input_set.inputs.get("roic")

    st.markdown("현재 가격이 요구하는 수익성의 질을 ROIC와 재투자율로 나눠 봅니다.")
    st.code(
        "ROIC = NOPAT / 투하자본\n"
        "경제적 이익 = NOPAT - 투하자본 × WACC\n"
        "재투자율 = 성장률 / ROIC\n"
        "현재 NOPAT 기준: EV/NOPAT = (1 - g/ROIC) / (WACC - g)\n"
        "투하자본 기준: EV = 투하자본 × (미래 ROIC - g) / (WACC - g)\n"
        "→ 미래 ROIC = g + EV × (WACC - g) / 투하자본",
        language="text",
    )

    if enterprise_value is None or nopat is None or invested_capital is None or roic is None:
        st.error("ROIC 분석에 필요한 EV, NOPAT, 투하자본 또는 ROIC가 없습니다. 먼저 데이터 검산을 확인하세요.")
        return

    c1, c2, c3 = st.columns(3)
    wacc = c1.slider("ROIC WACC", min_value=5.0, max_value=13.0, value=9.0, step=0.5) / 100.0
    growth_rate = c2.slider("목표 성장률 g", min_value=0.0, max_value=10.0, value=3.0, step=0.5) / 100.0
    target_roic = c3.slider("목표 ROIC", min_value=5.0, max_value=40.0, value=25.0, step=0.5) / 100.0

    economic_profit = calc_economic_profit(float(nopat), float(invested_capital), wacc)
    ev_nopat = calc_ev_nopat_multiple(float(enterprise_value), float(nopat))
    max_ev_nopat = calc_max_ev_nopat_multiple(wacc, growth_rate)
    implied_roic = calc_implied_roic_from_value_driver(ev_nopat, wacc, growth_rate)
    implied_future_roic = calc_implied_future_roic_from_invested_capital(
        float(enterprise_value), float(invested_capital), wacc, growth_rate
    )
    reinvestment_rate = calc_reinvestment_rate(growth_rate, target_roic)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("현재 ROIC", format_ratio(roic), delta=f"WACC 대비 {format_ratio(float(roic) - wacc)}")
    m2.metric("주가 내포 미래 ROIC", format_ratio(implied_future_roic))
    m3.metric("경제적 이익", format_krw(economic_profit))
    m4.metric("EV/NOPAT", _format_multiple(ev_nopat))

    d1, d2, d3 = st.columns(3)
    d1.metric("현재 NOPAT 기준 역산", _format_roic_solution(implied_roic))
    d2.metric("1단계 공식 최대 EV/NOPAT", _format_multiple(max_ev_nopat))
    d3.metric("현재 대비 미래 ROIC 배수", _format_multiple(None if implied_future_roic is None or not roic else implied_future_roic / float(roic)))

    if economic_profit < 0:
        st.warning(
            "현재 ROIC가 선택한 WACC보다 낮아 경제적 이익이 음수입니다. "
            "즉 현재 수익력만 놓고 보면 자본비용을 아직 충분히 넘지 못합니다."
        )
    else:
        st.info("현재 ROIC가 선택한 WACC를 넘어서고 있어 현재 수익력은 경제적 이익을 만들고 있습니다.")

    if implied_roic is None:
        st.warning(
            "현재 NOPAT를 고정한 EV/NOPAT 공식에서는 해가 없습니다. "
            f"선택한 WACC/g에서 이 공식이 설명할 수 있는 최대 배수는 {_format_multiple(max_ev_nopat)}인데, "
            f"현재 배수는 {_format_multiple(ev_nopat)}이기 때문입니다."
        )

    if implied_future_roic is not None and implied_future_roic >= 0.4:
        st.warning(
            "투하자본 기준으로 역산한 미래 ROIC가 매우 높습니다. "
            "이 값은 현재 주가가 단순히 현재 이익의 연장이 아니라 큰 폭의 정상화 이익, 높은 마진, 또는 긴 경쟁우위 기간을 요구한다는 뜻입니다."
        )

    st.markdown("#### 숫자 읽는 법")
    st.info(
        "요약하면 현재 수익성은 자본비용을 살짝 밑돌고, 현재 주가는 현재 이익만으로 설명되지 않습니다. "
        "따라서 시장은 큰 폭의 이익 정상화, 마진 개선, 고부가 제품 믹스, 또는 긴 경쟁우위 기간을 요구하고 있다고 읽어야 합니다."
    )
    st.table(pd.DataFrame(build_roic_metric_explanations()))

    st.markdown("#### 목표 ROIC별 필요 재투자율")
    st.caption(
        "재투자율 = 성장률 / ROIC입니다. 25%는 제한이 아니라 비교 기준입니다. "
        "높은 성장률을 낮은 ROIC로 만들려면 이익 대부분을 다시 투자해야 합니다."
    )
    r1, r2 = st.columns([1, 2])
    r1.metric("선택한 목표 ROIC의 필요 재투자율", format_ratio(reinvestment_rate))
    if reinvestment_rate is not None and reinvestment_rate > 1:
        r2.warning("필요 재투자율이 100%를 넘습니다. 이 성장률은 현재 이익 전부를 재투자해도 부족하다는 뜻입니다.")
    else:
        r2.info("같은 성장률이라도 ROIC가 높을수록 필요한 재투자율은 낮아집니다.")

    reinvestment_grid = _reinvestment_matrix(
        growth_rates=[0.02, 0.03, 0.05, 0.07, 0.10],
        roic_values=[0.08, 0.12, 0.16, 0.20, 0.25, 0.30, 0.40],
    )
    st.dataframe(
        reinvestment_grid.style.format(_format_reinvestment_cell).background_gradient(cmap="RdYlGn_r", axis=None),
        use_container_width=True,
    )

    with st.expander("입력값 출처와 계산 흐름"):
        st.markdown(
            f"""
            - 영업이익: `{format_krw(operating_income)}`
            - 세율: `{format_ratio(tax_rate)}`
            - NOPAT: `{format_krw(nopat)}`
            - 자본총계: `{format_krw(total_equity)}`
            - 순부채: `{format_krw(net_debt)}`
            - 투하자본: `{format_krw(invested_capital)}`
            - 현재 NOPAT 기준 역산: `{_format_roic_solution(implied_roic)}`
            - 주가 내포 미래 ROIC: `{format_ratio(implied_future_roic)}`
            - 공식: `ROIC = NOPAT / 투하자본`, `미래 ROIC = g + EV × (WACC - g) / 투하자본`
            """
        )


def render_relative_valuation_tab(input_set: ValuationInputSet) -> None:
    market_cap = input_set.inputs.get("market_cap")
    enterprise_value = input_set.inputs.get("enterprise_value")
    revenue = input_set.inputs.get("revenue")
    nopat = input_set.inputs.get("nopat")
    net_income = input_set.inputs.get("net_income")
    eps = input_set.inputs.get("eps")
    price = input_set.inputs.get("price")
    total_equity = input_set.inputs.get("total_equity")
    tax_rate = input_set.inputs.get("tax_rate") or 0.183

    st.markdown("상대가치는 싸다/비싸다 결론이 아니라, 현재 가격을 여러 분모로 나눠 시장의 요구조건을 보는 보조 렌즈입니다.")
    st.code(
        "P/E = 시가총액 / 순이익\n"
        "EPS 기준 P/E = 주가 / EPS\n"
        "P/B = 시가총액 / 자본총계\n"
        "내포 ROE = g + P/B × (요구수익률 - g)\n"
        "EV/Sales = EV / 매출\n"
        "필요 NOPAT margin = EV/Sales × (WACC - g) / ((1 - g/ROIC) × (1 + g))\n"
        "필요 영업이익률 = 필요 NOPAT margin / (1 - 세율)",
        language="text",
    )

    if market_cap is None or enterprise_value is None:
        st.error("상대가치 분석에 필요한 시가총액 또는 EV가 없습니다. 먼저 데이터 검산을 확인하세요.")
        return

    c1, c2, c3, c4 = st.columns(4)
    required_return = c1.slider("Equity 요구수익률", min_value=5.0, max_value=15.0, value=10.0, step=0.5) / 100.0
    wacc = c2.slider("Relative WACC", min_value=5.0, max_value=13.0, value=9.0, step=0.5) / 100.0
    growth_rate = c3.slider("Relative 성장률 g", min_value=0.0, max_value=8.0, value=3.0, step=0.5) / 100.0
    target_roic = c4.slider("Relative 목표 ROIC", min_value=5.0, max_value=40.0, value=25.0, step=0.5) / 100.0

    price_to_earnings = calc_price_to_earnings(market_cap, net_income)
    pe_from_eps = calc_pe_from_eps(price, eps)
    price_to_book = calc_price_to_book(market_cap, total_equity)
    ev_sales = calc_ev_to_sales(enterprise_value, revenue)
    ev_nopat = calc_ev_to_nopat(enterprise_value, nopat)
    implied_roe = calc_implied_roe_from_pb(price_to_book, required_return, growth_rate)
    implied_nopat_margin = calc_implied_nopat_margin_from_ev_sales(ev_sales, wacc, growth_rate, target_roic)
    implied_operating_margin = calc_implied_operating_margin_from_ev_sales(
        ev_sales, wacc, growth_rate, target_roic, float(tax_rate)
    )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("P/E", _format_multiple(price_to_earnings))
    m2.metric("P/B", _format_multiple(price_to_book))
    m3.metric("P/B 내포 ROE", format_ratio(implied_roe))
    m4.metric("EV/Sales", _format_multiple(ev_sales))

    n1, n2, n3, n4 = st.columns(4)
    n1.metric("EPS 기준 P/E", _format_multiple(pe_from_eps))
    n2.metric("EV/Sales 필요 NOPAT margin", format_ratio(implied_nopat_margin))
    n3.metric("EV/Sales 필요 영업이익률", format_ratio(implied_operating_margin))
    n4.metric("EV/NOPAT", _format_multiple(ev_nopat))

    if price_to_earnings is not None and pe_from_eps is not None:
        pe_gap = abs(price_to_earnings - pe_from_eps) / price_to_earnings
        if pe_gap >= 0.02:
            st.warning(
                "시가총액 기준 P/E와 EPS 기준 P/E가 다릅니다. "
                "이는 현재가, 주식수, 시가총액 기준 시점이나 보통주/우선주 처리 차이 때문일 수 있어 시장 데이터 검산이 필요합니다."
            )

    if implied_roe is not None and implied_roe >= 0.3:
        st.warning(
            "P/B 기준 내포 ROE가 매우 높습니다. 이는 장부자본 대비 현재 주가가 높은 수익성 회복 또는 긴 초과수익 기간을 요구한다는 뜻입니다."
        )
    if implied_operating_margin is not None and implied_operating_margin >= 0.4:
        st.warning(
            "EV/Sales 기준 필요 영업이익률이 매우 높습니다. 매출 규모 확대만으로는 부족하고 제품 믹스, 마진, 재투자 효율을 함께 검증해야 합니다."
        )

    st.markdown("#### 숫자 읽는 법")
    st.info(
        "P/B와 EV/Sales가 높게 나오면 그 자체가 결론은 아닙니다. "
        "중요한 질문은 이 배수를 정당화할 ROE, 마진, 성장률이 현실적인가입니다."
    )
    st.table(pd.DataFrame(build_relative_metric_explanations()))

    with st.expander("입력값 출처와 계산 흐름"):
        st.markdown(
            f"""
            - 시가총액: `{format_krw(market_cap)}`
            - EV: `{format_krw(enterprise_value)}`
            - 매출: `{format_krw(revenue)}`
            - NOPAT: `{format_krw(nopat)}`
            - 순이익: `{format_krw(net_income)}`
            - EPS: `{_format_price(eps)}`
            - 자본총계: `{format_krw(total_equity)}`
            - 세율: `{format_ratio(tax_rate)}`
            - P/E 출처: 2025 감사보고서 Note 23의 보통주 귀속 순이익과 EPS
            """
        )


def render_cap_duration_tab(input_set: ValuationInputSet) -> None:
    enterprise_value = input_set.inputs.get("enterprise_value")
    nopat = input_set.inputs.get("nopat")
    invested_capital = input_set.inputs.get("invested_capital")
    roic = input_set.inputs.get("roic")

    st.markdown("CAP는 현재 가격이 요구하는 초과수익이 몇 년이나 지속되어야 하는지 보는 렌즈입니다.")
    st.code(
        "현재 수익력 가치 = NOPAT / WACC\n"
        "초과가치 = EV - 현재 수익력 가치\n"
        "연간 경제적 이익 = 투하자본 × (ROIC - WACC)\n"
        "단순 CAP = 초과가치 / 연간 경제적 이익\n"
        "할인 CAP = 연간 경제적 이익의 할인현재가치가 초과가치와 같아지는 기간",
        language="text",
    )

    if enterprise_value is None or nopat is None or invested_capital is None or roic is None:
        st.error("CAP 분석에 필요한 EV, NOPAT, 투하자본 또는 ROIC가 없습니다. 먼저 데이터 검산을 확인하세요.")
        return

    c1, c2, c3 = st.columns(3)
    wacc = c1.slider("CAP WACC", min_value=5.0, max_value=13.0, value=9.0, step=0.5) / 100.0
    reference_growth = c2.slider("참고 성장률 g", min_value=0.0, max_value=8.0, value=3.0, step=0.5) / 100.0
    implied_future_roic = calc_implied_future_roic_from_invested_capital(
        float(enterprise_value), float(invested_capital), wacc, reference_growth
    )
    default_normalized_roic = min(120.0, max(10.0, round((implied_future_roic or float(roic)) * 100.0)))
    normalized_roic = c3.slider(
        "정상화 ROIC 가정",
        min_value=5.0,
        max_value=120.0,
        value=float(default_normalized_roic),
        step=1.0,
    ) / 100.0

    no_growth_value = calc_no_growth_value(float(nopat), wacc)
    excess_value = calc_future_expectation_value(float(enterprise_value), no_growth_value)
    current_annual_ep = calc_annual_economic_profit_from_roic(float(invested_capital), float(roic), wacc)
    normalized_annual_ep = calc_annual_economic_profit_from_roic(float(invested_capital), normalized_roic, wacc)
    simple_cap = calc_simple_payback_years(excess_value, normalized_annual_ep)
    discounted_cap = calc_discounted_cap_years(excess_value, normalized_annual_ep, wacc)
    perpetuity_ep_value = None if normalized_annual_ep is None or normalized_annual_ep <= 0 else normalized_annual_ep / wacc

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("초과가치", format_krw(excess_value))
    m2.metric("현재 연간 경제적 이익", format_krw(current_annual_ep))
    m3.metric("정상화 연간 경제적 이익", format_krw(normalized_annual_ep))
    m4.metric("단순 CAP", _format_years(simple_cap))

    d1, d2, d3 = st.columns(3)
    d1.metric("할인 CAP", _format_years(discounted_cap))
    d2.metric("경제적 이익 영구가치", format_krw(perpetuity_ep_value))
    d3.metric("참고 주가 내포 미래 ROIC", format_ratio(implied_future_roic))

    if current_annual_ep is not None and current_annual_ep <= 0:
        st.warning(
            "현재 ROIC가 WACC보다 낮아 현재 연간 경제적 이익은 음수입니다. "
            "따라서 현재 수익성 그대로는 경쟁우위 기간을 계산할 수 없고, 먼저 정상화 ROIC 회복 가정이 필요합니다."
        )

    if discounted_cap is None and excess_value > 0:
        st.warning(
            "선택한 정상화 ROIC로 만든 연간 경제적 이익은, 영구히 지속된다고 가정해도 현재 초과가치를 할인 기준으로 모두 설명하지 못합니다. "
            "이는 시장 가격이 더 높은 정상화 ROIC, 성장하는 경제적 이익, 또는 다른 비영업 가치까지 요구한다는 신호입니다."
        )

    st.markdown("#### 숫자 읽는 법")
    st.info(
        "CAP는 '좋은 수익성이 있다'에서 한 걸음 더 들어가 그 수익성이 얼마나 오래 지속되어야 하는지 묻습니다. "
        "삼성전기처럼 현재 ROIC가 낮고 가격이 높은 경우에는 CAP가 길게 나오거나 불가능으로 나오는데, "
        "이때 핵심 질문은 고부가 MLCC, FC-BGA, 전장 부품이 실제로 ROIC를 얼마나 회복시킬 수 있느냐입니다."
    )
    st.table(pd.DataFrame(build_cap_metric_explanations()))

    st.markdown("#### ROIC별 초과수익 기간 표")
    st.caption("각 ROIC가 매년 같은 경제적 이익을 만든다고 놓고, 5년/10년/15년/20년/30년 동안의 할인현재가치를 비교합니다.")
    periods = [5, 10, 15, 20, 30]
    table_rows = build_cap_duration_table(
        excess_value=excess_value,
        invested_capital=float(invested_capital),
        roic_values=[0.12, 0.20, 0.40, 0.70, 1.00, 1.20],
        wacc=wacc,
        periods=periods,
    )
    st.dataframe(_cap_duration_rows(table_rows, periods), use_container_width=True, hide_index=True)

    with st.expander("입력값 출처와 계산 흐름"):
        st.markdown(
            f"""
            - EV: `{format_krw(enterprise_value)}`
            - NOPAT: `{format_krw(nopat)}`
            - WACC: `{format_ratio(wacc)}`
            - 투하자본: `{format_krw(invested_capital)}`
            - 현재 ROIC: `{format_ratio(roic)}`
            - 정상화 ROIC 가정: `{format_ratio(normalized_roic)}`
            - 현재 수익력 가치: `{format_krw(no_growth_value)}`
            - 초과가치: `{format_krw(excess_value)}`
            - 공식: `초과가치 = EV - NOPAT / WACC`, `연간 경제적 이익 = 투하자본 × (ROIC - WACC)`
            """
        )


def main() -> None:
    st.set_page_config(page_title="삼성전기 가치분석", layout="wide")
    st.title("삼성전기 시장내포 가치분석")
    st.caption("Phase 1-7: 출처와 검산, Reverse DCF, 가치 분해, 매출·마진, ROIC, 상대가치, CAP를 함께 봅니다.")

    observations = load_metric_observations(METRICS_PATH)
    market = load_market_data(MARKET_PATH)
    input_set, checks, derived = run_audit(observations, market)
    all_observations = observations + derived

    st.subheader("시장 기준")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("현재가", _format_price(market["price"]))
    c2.metric("시가총액", format_krw(market["market_cap"]))
    c3.metric("직접 계산 EV", format_krw(input_set.inputs.get("enterprise_value")))
    c4.metric("시장 데이터 기준일", market["market_data_as_of"])

    st.subheader("핵심 입력값")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("2025 매출", format_krw(input_set.inputs.get("revenue")))
    k2.metric("2025 영업이익", format_krw(input_set.inputs.get("operating_income")))
    k3.metric("2025 FCF", format_krw(input_set.inputs.get("fcf")))
    k4.metric("계산 ROIC", format_ratio(input_set.inputs.get("roic")))

    q1, q2 = st.columns(2)
    q1.metric("2026 Q1 매출", format_krw(input_set.inputs.get("latest_quarter_revenue")))
    q2.metric("2026 Q1 영업이익", format_krw(input_set.inputs.get("latest_quarter_operating_income")))

    (
        tab_audit,
        tab_inputs,
        tab_reverse_dcf,
        tab_value_attribution,
        tab_margin_scenario,
        tab_roic,
        tab_relative,
        tab_cap,
        tab_formula,
        tab_source,
    ) = st.tabs(
        [
            "1. 검산",
            "2. 입력값",
            "3. Reverse DCF",
            "4. Value Attribution",
            "5. 매출·마진",
            "6. ROIC",
            "7. 상대가치",
            "8. CAP",
            "9. 공식",
            "10. 출처 상세",
        ]
    )

    with tab_audit:
        st.markdown("검산이 통과하지 않은 값은 다음 가치평가 렌즈로 넘기기 전에 확인합니다.")
        st.dataframe(_check_rows(checks), use_container_width=True, hide_index=True)

    with tab_inputs:
        st.markdown("같은 입력값을 Reverse DCF, Value Attribution, ROIC, 상대가치 렌즈가 공유합니다.")
        st.dataframe(_observation_rows(all_observations), use_container_width=True, hide_index=True)

    with tab_reverse_dcf:
        render_reverse_dcf_tab(input_set)

    with tab_value_attribution:
        render_value_attribution_tab(input_set)

    with tab_margin_scenario:
        render_margin_scenario_tab(input_set)

    with tab_roic:
        render_roic_reinvestment_tab(input_set)

    with tab_relative:
        render_relative_valuation_tab(input_set)

    with tab_cap:
        render_cap_duration_tab(input_set)

    with tab_formula:
        st.markdown(
            """
            - `FCF = 영업활동현금흐름 - CAPEX`
            - `순부채 = 단기차입금 + 장기차입금 - 현금`
            - `EV = 시가총액 + 순부채`
            - `NOPAT = 영업이익 × (1 - 세율)`
            - `투하자본 = 자본총계 + 순부채`
            - `ROIC = NOPAT / 투하자본`
            - `경제적 이익 = NOPAT - 투하자본 × WACC`
            - `재투자율 = 성장률 / ROIC`
            - `EV/NOPAT = (1 - g/ROIC) / (WACC - g)`
            - `P/E = 시가총액 / 순이익`
            - `EPS 기준 P/E = 주가 / EPS`
            - `P/B = 시가총액 / 자본총계`
            - `내포 ROE = g + P/B × (요구수익률 - g)`
            - `EV/Sales = EV / 매출`
            - `초과가치 = EV - NOPAT / WACC`
            - `연간 경제적 이익 = 투하자본 × (ROIC - WACC)`
            - `단순 CAP = 초과가치 / 연간 경제적 이익`
            """
        )
        st.warning("이 화면은 투자 권유가 아니라 다음 가치평가 단계로 넘길 입력값의 신뢰도를 확인하는 화면입니다.")

    with tab_source:
        selected_label = st.selectbox(
            "출처를 볼 입력값",
            options=[obs.label for obs in all_observations],
        )
        selected = next(obs for obs in all_observations if obs.label == selected_label)
        render_source_panel(selected)


if __name__ == "__main__":
    main()
