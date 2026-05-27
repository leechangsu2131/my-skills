from __future__ import annotations

from pathlib import Path
import json

import sys
import os
# 프로젝트 루트 디렉토리를 sys.path에 추가하여 어디서 실행하든 모듈을 찾을 수 있게 함
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

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
from valuation_app.narrative_consistency import (
    build_narrative_explanation,
    get_company_narratives,
)
from valuation_app.synthesis import (
    build_next_quarter_checklist,
    build_synthesis_explanation,
    evaluate_signals,
)
from valuation_app.advanced_reverse import (
    calc_implied_expected_return,
    calc_implied_growth_from_peg,
    calc_implied_market_share,
    decompose_expected_return,
)
from valuation_app.export_builder import build_export_json, build_export_markdown
from valuation_app.export_saver import save_analysis, get_save_history
from valuation_app.reverse_dcf import build_required_fcf_matrix, calc_normalized_fcf, required_fcf_multiple
from valuation_app.risk_downside import (
    build_margin_wacc_sensitivity,
    build_risk_metric_explanations,
    build_scenario_table,
    build_wacc_growth_sensitivity,
    rank_value_drivers,
)
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
DATA_ROOT = ROOT / "data" / "valuation"


def _discover_tickers() -> list[tuple[str, str]]:
    """data/valuation/ 아래의 종목 폴더를 스캔하여 (ticker, display_label) 리스트 반환."""
    if not DATA_ROOT.exists():
        return []
    results = []
    for d in sorted(DATA_ROOT.iterdir()):
        if not d.is_dir():
            continue
        market_path = d / "normalized" / "market.json"
        if market_path.exists():
            try:
                with market_path.open("r", encoding="utf-8") as f:
                    mkt = json.load(f)
                label = f"{mkt.get('company_name', d.name)} ({d.name})"
                results.append((d.name, label))
            except Exception:
                results.append((d.name, d.name))
        else:
            results.append((d.name, d.name))
    return results


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
        dart_val_str = _display_value(obs)
        yf_val_str = "-"
        diff_str = "-"
        
        if hasattr(obs, 'yf_value') and obs.yf_value is not None and obs.yf_value != 0:
            if obs.unit == "ratio":
                yf_val_str = format_ratio(obs.yf_value)
            elif obs.unit == "KRW/share":
                yf_val_str = _format_price(obs.yf_value)
            else:
                yf_val_str = format_krw(obs.yf_value)
                
            if obs.value is not None:
                diff = (obs.value - obs.yf_value) / abs(obs.yf_value) * 100
                diff_str = f"{diff:+.2f}%"
                if diff == 0:
                    diff_str = "0.00%"
                
        rows.append(
            {
                "입력값": obs.label,
                "기간": obs.period,
                "DART 값": dart_val_str,
                "yfinance 값": yf_val_str,
                "오차율": diff_str,
                "출처": source_label(obs.source_method),
                "보고서": obs.statement_name or "-",
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


def render_risk_downside_tab(input_set: ValuationInputSet) -> None:
    enterprise_value = input_set.inputs.get("enterprise_value")
    annual_revenue = input_set.inputs.get("revenue")
    tax_rate = input_set.inputs.get("tax_rate") or 0.183
    latest_quarter_revenue = input_set.inputs.get("latest_quarter_revenue")
    latest_quarter_operating_income = input_set.inputs.get("latest_quarter_operating_income")

    st.markdown("핵심 가정이 빗나가면 가치가 얼마나 흔들리는지 민감도 표와 시나리오로 봅니다.")
    st.code(
        "추정 EV = 정상화 FCF / (WACC - g)\n"
        "정상화 FCF = 매출 × 영업이익률 × (1 - 세율) × FCF 전환율\n"
        "괴리율 = (추정 EV - 현재 EV) / 현재 EV",
        language="text",
    )

    if enterprise_value is None or annual_revenue is None:
        st.error("리스크 분석에 필요한 EV 또는 매출이 없습니다. 먼저 데이터 검산을 확인하세요.")
        return

    latest_margin = 0.11
    if latest_quarter_revenue and latest_quarter_operating_income:
        latest_margin = round(float(latest_quarter_operating_income) / float(latest_quarter_revenue), 3)

    c1, c2, c3 = st.columns(3)
    base_margin = c1.slider(
        "Risk 정상화 영업이익률", min_value=0.0, max_value=80.0,
        value=round(latest_margin * 100, 1), step=0.5,
    ) / 100.0
    fcf_conversion = c2.slider("Risk FCF 전환율", min_value=10.0, max_value=120.0, value=70.0, step=5.0) / 100.0
    delta_pct = c3.slider("가치 동인 변동폭", min_value=0.5, max_value=5.0, value=1.0, step=0.5) / 100.0

    current_ev = float(enterprise_value)
    base_revenue = float(annual_revenue)

    # --- WACC/g 민감도 표 ---
    st.markdown("#### WACC / 영구성장률 민감도: 추정 EV")
    st.caption("행은 WACC, 열은 영구성장률입니다. 각 칸은 해당 가정에서의 추정 EV(조원)입니다.")
    wacc_grid = [0.07, 0.08, 0.09, 0.10, 0.11, 0.12]
    growth_grid = [0.01, 0.02, 0.03, 0.04]
    ev_matrix_rows = build_wacc_growth_sensitivity(
        base_revenue=base_revenue, operating_margin=base_margin, tax_rate=float(tax_rate),
        fcf_conversion=fcf_conversion, wacc_values=wacc_grid, growth_values=growth_grid,
        current_ev=current_ev, metric="implied_ev",
    )
    ev_matrix = pd.DataFrame(ev_matrix_rows).set_index("wacc")
    ev_matrix.index = [format_ratio(v) for v in ev_matrix.index]
    ev_matrix.columns = [format_ratio(v) for v in ev_matrix.columns]
    ev_matrix.index.name = "WACC \\ g"
    st.dataframe(
        ev_matrix.style.format(lambda v: _format_sensitivity_cell(v, "krw_trillion")).background_gradient(
            cmap="RdYlGn", axis=None
        ),
        use_container_width=True,
    )

    # --- WACC/g 괴리율 ---
    st.markdown("#### WACC / 영구성장률 민감도: 현재 EV 대비 괴리율")
    st.caption("양수(녹색)면 현재 가격 대비 저평가 방향, 음수(붉은색)면 고평가 방향입니다. 단 모형 가정에 강하게 의존합니다.")
    gap_matrix_rows = build_wacc_growth_sensitivity(
        base_revenue=base_revenue, operating_margin=base_margin, tax_rate=float(tax_rate),
        fcf_conversion=fcf_conversion, wacc_values=wacc_grid, growth_values=growth_grid,
        current_ev=current_ev, metric="ev_gap",
    )
    gap_matrix = pd.DataFrame(gap_matrix_rows).set_index("wacc")
    gap_matrix.index = [format_ratio(v) for v in gap_matrix.index]
    gap_matrix.columns = [format_ratio(v) for v in gap_matrix.columns]
    gap_matrix.index.name = "WACC \\ g"
    st.dataframe(
        gap_matrix.style.format(_format_coverage_cell).background_gradient(
            cmap="RdYlGn", axis=None
        ),
        use_container_width=True,
    )

    # --- 마진/WACC 민감도 ---
    st.markdown("#### 영업이익률 / WACC 민감도: 괴리율")
    st.caption("행은 영업이익률, 열은 WACC입니다. 영구성장률 3%를 가정합니다.")
    margin_grid = [0.08, 0.12, 0.20, 0.35, 0.50, 0.80]
    margin_wacc_grid = [0.07, 0.08, 0.09, 0.10, 0.11, 0.12]
    margin_wacc_rows = build_margin_wacc_sensitivity(
        base_revenue=base_revenue, tax_rate=float(tax_rate), fcf_conversion=fcf_conversion,
        margin_values=margin_grid, wacc_values=margin_wacc_grid, terminal_growth=0.03,
        current_ev=current_ev, metric="ev_gap",
    )
    mw_matrix = pd.DataFrame(margin_wacc_rows).set_index("margin")
    mw_matrix.index = [format_ratio(v) for v in mw_matrix.index]
    mw_matrix.columns = [format_ratio(v) for v in mw_matrix.columns]
    mw_matrix.index.name = "OPM \\ WACC"
    st.dataframe(
        mw_matrix.style.format(_format_coverage_cell).background_gradient(
            cmap="RdYlGn", axis=None
        ),
        use_container_width=True,
    )

    # --- 베어/베이스/불 시나리오 ---
    st.markdown("#### 베어 / 베이스 / 불 시나리오")
    st.caption("각 시나리오는 매출 성장률, 영업이익률, WACC, 영구성장률을 달리한 가정 세트입니다.")
    scenarios = [
        {"name": "🐻 베어", "revenue_growth": 0.0, "operating_margin": 0.08, "wacc": 0.11, "terminal_growth": 0.02},
        {"name": "⚖️ 베이스", "revenue_growth": 0.10, "operating_margin": base_margin, "wacc": 0.09, "terminal_growth": 0.03},
        {"name": "🐂 불", "revenue_growth": 0.30, "operating_margin": 0.18, "wacc": 0.08, "terminal_growth": 0.03},
    ]
    scenario_results = build_scenario_table(
        base_revenue=base_revenue, scenarios=scenarios,
        tax_rate=float(tax_rate), fcf_conversion=fcf_conversion, current_ev=current_ev,
    )

    scenario_cols = st.columns(3)
    for i, result in enumerate(scenario_results):
        with scenario_cols[i]:
            st.markdown(f"##### {result['시나리오']}")
            st.metric("추정 EV", format_krw(result["추정 EV"]))
            gap_val = result["현재 EV 대비 괴리율"]
            gap_label = format_ratio(gap_val) if gap_val is not None else "-"
            st.metric("괴리율", gap_label)
            st.caption(
                f"매출 +{format_ratio(result['매출 성장률'])} · OPM {format_ratio(result['영업이익률'])} · "
                f"WACC {format_ratio(result['WACC'])} · g {format_ratio(result['영구성장률'])}"
            )

    scenario_df = []
    for r in scenario_results:
        scenario_df.append({
            "시나리오": r["시나리오"],
            "정상화 FCF": format_krw(r["정상화 FCF"]),
            "추정 EV": format_krw(r["추정 EV"]),
            "괴리율": format_ratio(r["현재 EV 대비 괴리율"]),
        })
    st.dataframe(scenario_df, use_container_width=True, hide_index=True)

    # --- 가치 동인 순위 ---
    st.markdown("#### 가치 동인 순위")
    st.caption(f"각 변수를 {format_ratio(delta_pct)} 움직였을 때 추정 EV가 얼마나 변하는지 비교합니다. 절대 변동이 큰 순서로 정렬됩니다.")
    drivers = rank_value_drivers(
        base_revenue=base_revenue, base_margin=base_margin,
        base_tax_rate=float(tax_rate), base_fcf_conversion=fcf_conversion,
        base_wacc=0.09, base_terminal_growth=0.03, current_ev=current_ev,
        delta=delta_pct,
    )
    driver_rows = []
    for d in drivers:
        driver_rows.append({
            "변수": d["변수"],
            "기준값": format_ratio(d["기준값"]) if isinstance(d["기준값"], float) and d["기준값"] < 10 else format_krw(d["기준값"]),
            "변동폭": format_ratio(d["변동폭"]),
            "EV 변화": format_krw(d["EV 변화"]),
            "EV 변화율": format_ratio(d["EV 변화율"]),
        })
    st.dataframe(driver_rows, use_container_width=True, hide_index=True)

    most_sensitive = drivers[0]["변수"] if drivers else "-"
    st.info(f"현재 가정에서 가장 민감한 변수는 **{most_sensitive}**입니다. 이 변수가 기대와 다르게 움직이면 가격 충격이 가장 큽니다.")

    # --- 숫자 읽는 법 ---
    st.markdown("#### 숫자 읽는 법")
    st.info(
        "민감도 표는 정답이 아니라 '무엇이 틀리면 얼마나 흔들리는가'를 미리 연습하는 도구입니다. "
        "괴리율이 큰 조합은 해당 가정이 빗나갈 때 가격 하락 리스크가 크다는 신호입니다."
    )
    st.table(pd.DataFrame(build_risk_metric_explanations()))

    with st.expander("입력값 출처와 계산 흐름"):
        st.markdown(
            f"""
            - 매출: `{format_krw(annual_revenue)}`
            - 정상화 영업이익률: `{format_ratio(base_margin)}`
            - 세율: `{format_ratio(tax_rate)}`
            - FCF 전환율: `{format_ratio(fcf_conversion)}`
            - 현재 EV: `{format_krw(enterprise_value)}`
            - 공식: `추정 EV = 매출 × OPM × (1 - 세율) × FCF전환율 / (WACC - g)`
            """
        )


def render_narrative_tab(ticker: str, company_name: str) -> None:
    st.markdown(build_narrative_explanation(company_name))

    stories = get_company_narratives(ticker)
    
    for story in stories:
        with st.container():
            st.markdown(f"### {story['title']}")
            st.write(story["description"])
            
            c1, c2 = st.columns([1, 1])
            with c1:
                st.markdown("**🔍 확인할 숫자**")
                for metric in story["metrics_to_watch"]:
                    st.markdown(f"- {metric}")
                    
                st.markdown("**🔗 연결되는 렌즈**")
                for tab in story["related_tabs"]:
                    st.markdown(f"- {tab}")
                    
            with c2:
                st.success(f"**📈 Bull Signal (스토리가 맞을 때)**\n\n{story['bull_signal']}")
                st.error(f"**📉 Bear Signal (스토리가 틀릴 때)**\n\n{story['bear_signal']}")
                
            st.divider()


def render_synthesis_tab(input_set: ValuationInputSet) -> None:
    st.markdown(build_synthesis_explanation())
    
    st.markdown("### 📊 수렴과 발산 (Signal Summary)")
    st.caption("여러 렌즈의 분석 결과를 모아 현재 주가에 내포된 시장의 기대치가 어떤 상태인지 종합합니다.")
    
    signals = evaluate_signals(input_set)
    if not signals:
        st.warning("입력값이 부족하여 종합 신호를 계산할 수 없습니다.")
    else:
        for signal in signals:
            status = signal["상태"]
            # 상태에 따른 색상 지정
            if "여유" in status or "우수" in status:
                color = "green"
            elif "부담" in status or "요구" in status or "파괴" in status:
                color = "red"
            else:
                color = "orange"
                
            st.markdown(f"**{signal['분야']}**: :{color}[{status}]")
            st.write(signal["해석"])
            if signal["수치 형태"] == "ratio":
                st.caption(f"산출된 지표 수치: {signal['핵심 수치']*100:.1f}%")
            else:
                st.caption(f"산출된 지표 수치: {signal['핵심 수치']:.1f}배")
            st.write("---")

    st.markdown("### ✅ 다음 분기 관전 포인트 (Checklist)")
    st.caption("다음 실적 발표 때 반드시 확인해서 시장의 기대치(위의 신호)가 충족되고 있는지 점검하세요.")
    
    checklist = build_next_quarter_checklist()
    for item in checklist:
        with st.expander(f"[{item['카테고리']}] {item['확인 포인트']}"):
            st.markdown(f"**판단 기준**: {item['판단 기준']}")


def render_peg_tab(input_set: ValuationInputSet, market: dict) -> None:
    st.markdown("### 멀티플 기반 단기 기대성장률 역산 (Implied Growth from PEG)")
    st.caption("현재 PER 수준과 산업/기업에 적정하다고 판단하는 PEG를 입력하면, 시장이 단기적으로 요구하는 이익 성장률을 역산합니다.")
    
    mc = market.get("market_cap")
    ni = input_set.inputs.get("net_income")
    
    if mc is None or ni is None or ni <= 0:
        st.warning("PER 산출을 위한 기초 데이터(시가총액, 양수의 순이익)가 부족합니다.")
        return
        
    per_actual = mc / ni
    
    col1, col2 = st.columns(2)
    col1.metric("현재 시장 적용 PER", f"{per_actual:.1f} 배", help="시가총액 / 최근 순이익")
    
    peg_val = col2.slider(
        "적정 기준 PEG 선택", 
        min_value=0.5, max_value=5.0, value=1.5, step=0.1,
        help="성숙 제조업 0.5~1.0, 일반 IT 1~2, 고성장 SaaS 2~4 수준"
    )
    
    implied_growth = calc_implied_growth_from_peg(per_actual, peg_val)
    if implied_growth is not None:
        fair_per = peg_val * (implied_growth * 100)
        
        st.success(
            f"적정 PEG **{peg_val:.1f}** 배를 가정할 때, 현재 PER({per_actual:.1f}배)을 정당화하려면 "
            f"시장은 단기적으로 **연평균 {implied_growth*100:.1f}%**의 이익 성장을 기대하고 있습니다."
        )
        
        st.markdown(
            f"""
            **[수식의 투명한 이해]**
            * **시장의 기대 성장률(%)** = `현재 PER ÷ 적용 PEG`
            * **역산 결과**: `{implied_growth*100:.1f}% = {per_actual:.1f}배 ÷ {peg_val:.1f}배`
            
            **[내포된 시나리오 검산]**
            * `현재 요구되는 적정 PER = 적용 PEG × 이익성장률(%)`
            * 만약 이 회사가 정말로 향후 **{implied_growth*100:.1f}%**씩 성장한다고 가정하면, 우리가 허용한 적정 PEG({peg_val:.1f}) 하에서 **지금 당장** 부여받을 수 있는 합당한 PER은 **{fair_per:.1f}배**가 됩니다.
            * 즉, 현재 주가(PER {per_actual:.1f}배)는 "회사가 향후 연 {implied_growth*100:.1f}%씩 고성장할 것"이라는 장밋빛 시나리오를 **현재 가격에 이미 100% 선반영(Priced-in)**하고 있다는 뜻입니다.
            * ⏳ **요구되는 지속 기간(Duration)**: 시장에서 통상적으로 보는 PEG 배수는 단 1년짜리 짝수 성장이 아닙니다. 현재 주가를 정당화하려면 저 엄청난 성장률(연 {implied_growth*100:.1f}%)을 **향후 3~5년간 쉼 없이 연속으로(CAGR)** 달성해내야 함을 암묵적으로 의미합니다.
            * ⚠️ **주의 (멀티플 수축)**: 고성장기가 끝나고 향후 이익성장률이 정상 수준(예: 10%)으로 둔화되면, 투자자들이 허용하는 PER도 평균 수준(10~15배)으로 급격히 회귀합니다(Multiple Contraction). 따라서 성장이 1~2년 만에 예상보다 빨리 꺾이는 순간 주가는 폭락할 수 있습니다.
            """
        )
        
        st.markdown("---")
        
        st.markdown("#### ⏳ 기간 및 멀티플 수축 기반 정밀 역산")
        st.caption("단순 PEG를 넘어, 'n년 뒤 평범한 주식(정상 PER)으로 돌아갈 때 내 기대수익률을 맞추려면 그동안 매년 몇 %씩 성장해야 하는가?'를 정밀하게 역산합니다.")
        
        hist_per = market.get("historical_average_per", 15.0)
        peer_per = market.get("peer_average_per", 15.0)
        st.info(f"💡 **파이프라인 자동 추출 기준점**: 과거 평균 PER **{hist_per:.1f}배** / 글로벌 Peer 평균 PER **{peer_per:.1f}배**")
        
        col_n, col_term, col_ret = st.columns(3)
        duration_n = col_n.slider("고성장 지속 기간 (n년)", min_value=1, max_value=15, value=5, step=1)
        terminal_per = col_term.slider("고성장 종료 후 정상 PER", min_value=5.0, max_value=50.0, value=float(hist_per), step=1.0)
        target_return = col_ret.slider(
            "투자자 목표 수익률 (%)", 
            min_value=0.0, max_value=30.0, value=10.0, step=1.0,
            help="투자자가 이 주식을 보유하는 동안 최소한 얻고자 하는 연평균 기대 수익률(예: 기회비용, 할인율 등). 0%로 두면 '본전'을 찾기 위한 성장률이 나옵니다."
        ) / 100.0
        
        if terminal_per > 0 and duration_n > 0:
            implied_g_contraction = ((per_actual / terminal_per) ** (1 / duration_n)) * (1 + target_return) - 1
            
            # Export용 Session State 저장
            st.session_state["export_peg_n_years"] = duration_n
            st.session_state["export_peg_terminal_per"] = terminal_per
            st.session_state["export_peg_implied_g"] = implied_g_contraction
            
            st.info(
                f"현재 주가를 정당화하려면, 이 회사는 **향후 {duration_n}년 동안 연평균 {implied_g_contraction*100:.1f}%씩 연속으로 이익이 성장**해야 합니다."
            )
            
            st.markdown(
                f"""
                **[시뮬레이션 해설]**
                * 투자자가 현재 **PER {per_actual:.1f}배**에 진입하여, 매년 **{target_return*100:.0f}%**의 목표 수익률을 달성한다고 가정합니다.
                * **{duration_n}년 뒤** 고성장이 끝나 시장의 환호가 식으면서 주식의 PER이 **{terminal_per:.1f}배**로 폭락(Multiple Contraction)한다고 가정합니다.
                * 이 끔찍한 멀티플 수축을 주가 하락 없이 모두 견뎌내고 내 수익률까지 챙기려면, 회사가 그 {duration_n}년 내내 **연평균 {implied_g_contraction*100:.1f}%**라는 무시무시한 속도로 이익을 불려줘야만 수학적으로 아귀가 맞습니다.
                * *💡 수식: 요구 성장률 = [ (현재 PER ÷ 미래 정상 PER)^(1/n) × (1 + 목표 수익률) ] - 1*
                """
            )

        st.markdown("---")
        st.markdown("#### 💡 이 성장률이 현실 가능한가?")
        st.markdown(
            f"단순히 PEG가 싸 보인다고 저평가가 아닙니다. "
            f"**연평균 {implied_growth*100:.1f}%**의 성장을 이뤄내려면 다음 질문들을 통과해야 합니다.\n\n"
            "- **지속 기간**: 이 폭발적인 성장을 과연 몇 년이나 유지할 수 있는가?\n"
            "- **시장 규모(TAM)**: 목표 성장을 달성할 만큼 전방 시장이 충분히 큰가?\n"
            "- **경쟁 심화**: 고성장 시장에 필연적으로 들어오는 경쟁자들을 막아낼 진입장벽이 있는가?\n"
            "- **마진 유지**: 점유율을 뺏기 위해 판관비나 가격 할인을 남발해 마진이 훼손되지는 않는가?\n"
            "- **자본 효율성(ROIC)**: 성장을 위해 번 돈보다 더 많은 돈을 때려 박아야 하는(현금 소모적) 구조는 아닌가?\n\n"
            "> *PEG 역산은 가치평가의 끝이 아니라, 위 질문들을 던지기 위한 **출발점**입니다.*"
        )
    st.divider()

    st.markdown("##### 📌 시장의 내포 기대수익률 & 기대 FCF 역산 (Implied Expected Return)")
    st.caption("현재 가격표(기업가치)와 할인율(WACC), 영구성장률(g)을 넣으면 **시장이 요구하는 기대 FCF**와 **내포 기대수익률**이 자동으로 역산됩니다.")
    
    ev = input_set.inputs.get("enterprise_value")
    fcf = input_set.inputs.get("fcf")
    if ev is not None and fcf is not None:
        col_w, col_g = st.columns(2)
        wacc = col_w.number_input("WACC (할인율, %)", min_value=1.0, max_value=30.0, value=9.0, step=0.5) / 100.0
        lt_growth = col_g.number_input("장기 영구성장률 (g, %)", min_value=-5.0, max_value=10.0, value=3.0, step=0.5) / 100.0
        
        if wacc > lt_growth:
            required_fcf = ev * (wacc - lt_growth)
            fcf_multiple = required_fcf / fcf if fcf > 0 else None
            
            st.markdown("---")
            m1, m2, m3, m4 = st.columns(4)
            current_yield = fcf / ev
            current_implied = current_yield + lt_growth

            m1.metric("현재 FCF", f"{fcf/1e12:.2f}조 원")
            m2.metric("시장이 요구하는 기대 FCF", f"{required_fcf/1e12:.2f}조 원")
            if fcf_multiple is not None:
                m3.metric("FCF 갭 배수", f"{fcf_multiple:.1f}배")
            m4.metric(
                "현재 가격의 내포 기대수익률",
                f"{wacc*100:.1f}%",
                help=(
                    f"기대 FCF({required_fcf/1e12:.1f}조)가 실현될 때 투자자가 얻는 수익률 = WACC.\n"
                    f"현재 FCF({fcf/1e12:.2f}조) 기준 실질 수익률은 {current_implied*100:.1f}%에 불과합니다."
                )
            )
            
            st.markdown("---")
            
            if fcf_multiple is not None and fcf_multiple > 5:
                st.error(
                    f"**시장은 현재 FCF({fcf/1e12:.2f}조)가 앞으로 {fcf_multiple:.0f}배({required_fcf/1e12:.1f}조)로 "
                    f"폭발적으로 성장할 것을 기대하고 있습니다.**  \n"
                    f"이 기대가 달성되어야만 투자자의 기대수익률 **{wacc*100:.1f}%**가 실현됩니다.  \n"
                    f"현재 FCF가 그대로 유지된다면 실질 내포 수익률은 **{current_implied*100:.1f}%**입니다."
                )
            elif fcf_multiple is not None and fcf_multiple > 2:
                st.warning(
                    f"시장은 현재 FCF 대비 {fcf_multiple:.1f}배의 성장({required_fcf/1e12:.1f}조)을 기대합니다.  \n"
                    f"이 기대가 충족될 때 내포 기대수익률: **{wacc*100:.1f}%**"
                )
            else:
                st.success(
                    f"현재 FCF 수준이 시장의 기대치({required_fcf/1e12:.1f}조)에 근접합니다.  \n"
                    f"내포 기대수익률: **{wacc*100:.1f}%**"
                )
            
            st.caption(
                f"수식: 기대 FCF = EV × (WACC − g) = {ev/1e12:.1f}조 × ({wacc*100:.1f}% − {lt_growth*100:.1f}%) = {required_fcf/1e12:.2f}조  |  "
                f"현재 내포 수익률 = FCF Yield + g = {current_yield*100:.1f}% + {lt_growth*100:.1f}% = {current_implied*100:.1f}%"
            )
        else:
            st.warning("WACC는 영구성장률(g)보다 커야 합니다.")


def render_tam_tab(input_set: ValuationInputSet, market: dict) -> None:
    st.markdown("### TAM 기반 시장 점유율 역산 (Implied Market Share)")
    st.caption("Reverse DCF가 요구하는 먼 미래의 필수 매출액을 달성하려면, 타겟 시장(TAM)에서 몇 %의 점유율을 차지해야 하는지 파악하여 현실성/버블 여부를 진단합니다.")
    
    # 1. 기초 데이터 및 파이프라인 앵커링
    current_rev = input_set.inputs.get("revenue", 0)
    current_tam = market.get("current_tam", 40000000000000)  # default 40T
    projected_tam = market.get("projected_tam_5yr", 60000000000000)  # default 60T
    
    current_share = (current_rev / current_tam) * 100 if current_tam > 0 else 0
    
    st.info(
        f"💡 **파이프라인 자동 추출 기준점 (Anchor)**  \n"
        f"- **현재 매출액**: {current_rev/1_000_000_000_000:.1f}조 원  \n"
        f"- **현재 글로벌 TAM**: {current_tam/1_000_000_000_000:.1f}조 원 👉 **(현재 시장 점유율: {current_share:.1f}%)**  \n"
        f"- **향후 예측 TAM**: {projected_tam/1_000_000_000_000:.1f}조 원"
    )
    
    st.markdown("#### 1. 요구 매출 및 TAM 시뮬레이션")
    
    target_rev_default = (current_rev / 1_000_000_000_000) * 1.5 if current_rev > 0 else 15.0
        
    col1, col2 = st.columns(2)
    req_rev = col1.number_input(
        "요구되는 타겟 매출 (조원, 예: 5년 뒤)", 
        min_value=1.0, max_value=1000.0, value=float(target_rev_default), step=1.0,
        help="Reverse DCF나 PEG 역산을 통해 도출된 미래 필수 달성 매출액을 입력합니다."
    )
    est_tam = col2.number_input(
        "해당 시점 글로벌 전체 TAM 예측치 (조원)", 
        min_value=10.0, max_value=5000.0, value=float(projected_tam/1_000_000_000_000), step=5.0
    )
    
    implied_share = calc_implied_market_share(req_rev, est_tam)
    if implied_share is not None:
        st.success(
            f"요구되는 타겟 매출 **{req_rev:.1f}조 원**을 달성하기 위해서는, "
            f"해당 시점 글로벌 시장(TAM {est_tam:.1f}조)에서 **{implied_share*100:.1f}%의 점유율**을 차지해야만 합니다."
        )
        
        st.markdown(
            f"""
            **[수식의 투명한 이해]**
            * `미래 요구 점유율(%) = 역산된 요구 매출({req_rev:.1f}조) ÷ 미래 예상 TAM({est_tam:.1f}조) = {implied_share*100:.1f}%`
            * 현재 시장 점유율 **{current_share:.1f}%** 대비 **{abs(implied_share*100 - current_share):.1f}%p**의 점유율 변동이 필요합니다.
            """
        )
        
        st.markdown("---")
        st.markdown(f"#### 💡 이 {implied_share*100:.1f}%라는 점유율이 현실 가능한가?")
        st.markdown(
            f"단순히 시장이 커진다고 내 매출이 저절로 오르는 것은 아닙니다. 현재 주가에 내포된 저 점유율을 달성하려면 다음의 질문들을 통과해야 합니다.\n\n"
            "- **TAM의 환상**: 우리가 설정한 미래 TAM({est_tam:.1f}조) 자체가 증권사나 업계의 과도한 장밋빛 전망(뻥튀기)은 아닌가?\n"
            "- **경쟁 강도**: 현재 1, 2위를 다투는 글로벌 경쟁자들이 순순히 저 점유율({implied_share*100:.1f}%)을 내어줄 것인가?\n"
            "- **기술적 해자(Moat)**: 경쟁사의 파이를 빼앗아올 만큼 압도적인 기술 격차나 가격 경쟁력을 새롭게 확보했는가?\n"
            "- **수익성 훼손**: 무리하게 점유율을 끌어올리기 위해 판관비를 쏟아붓거나 단가 인하를 단행하여, 결국 영업이익률(OPM)이 망가지는 '상처뿐인 영광'은 아닌가?\n\n"
            "> *TAM 역산은 요구 점유율을 계산하는 것으로 끝나는 것이 아니라, 비즈니스 모델의 한계를 묻는 **출발점**입니다.*"
        )

    st.divider()
    st.markdown("#### 2. 🚀 내포 기대치 역산 샌드박스 (Top-Down Implied Share)")
    st.caption("현재 주가를 정당화하기 위해(또는 목표 수익률을 내기 위해) **미래에 도대체 몇 %의 시장 점유율을 차지해야 하는지**를 역추산하여 현재 가격의 거품을 진단합니다.")
    
    # 2. 기초 변수 추출
    current_op = input_set.inputs.get("operating_income", 0)
    current_opm = (current_op / current_rev) * 100 if current_rev > 0 else 10.0
    tax_rate = input_set.inputs.get("tax_rate", 0.22)
    current_mcap = market.get("market_cap", 0)
    hist_per = market.get("historical_average_per", 15.0)
    
    col_a, col_b, col_c = st.columns(3)
    sim_n_years = col_a.slider("투자기간 (n년 뒤)", min_value=1, max_value=15, value=5, step=1)
    sim_tam_cagr = col_b.slider("글로벌 TAM 연평균 성장률 (%)", min_value=-10.0, max_value=50.0, value=10.0, step=1.0) / 100.0
    sim_target_return = col_c.slider("투자자 목표 수익률 (%)", min_value=0.0, max_value=30.0, value=0.0, step=1.0, help="0%로 두면 현재 시총을 정당화(본전)하기 위한 요구 점유율이 나옵니다.") / 100.0
    
    col_d, col_e, col_f = st.columns(3)
    sim_opm = col_d.slider("미래 목표 영업이익률 (OPM, %)", min_value=1.0, max_value=50.0, value=float(current_opm), step=1.0) / 100.0
    sim_per = col_e.slider("미래 타겟 PER (멀티플 수축 반영, 배)", min_value=5.0, max_value=50.0, value=float(hist_per), step=1.0)
    
    if current_mcap > 0 and current_tam > 0:
        # 역방향 계산 로직 (Reverse Engineering)
        target_future_mcap = current_mcap * ((1 + sim_target_return) ** sim_n_years)
        req_future_ni = target_future_mcap / sim_per
        req_future_op = req_future_ni / (1 - tax_rate)
        req_future_rev = req_future_op / sim_opm
        
        future_tam = current_tam * ((1 + sim_tam_cagr) ** sim_n_years)
        
        implied_target_share = req_future_rev / future_tam
        
        # Export용 Session State 저장
        st.session_state["export_tam_n_years"] = sim_n_years
        st.session_state["export_tam_cagr"] = sim_tam_cagr
        st.session_state["export_tam_target_return"] = sim_target_return
        st.session_state["export_tam_implied_share"] = implied_target_share
        st.session_state["export_tam_opm"] = sim_opm
        st.session_state["export_tam_per"] = sim_per
        
        st.markdown("##### 📊 가격표에 선반영된 요구 시장 점유율")
        
        res_col1, res_col2, res_col3, res_col4 = st.columns(4)
        res_col1.metric("목표 미래 시가총액", f"{target_future_mcap/1_000_000_000_000:.1f}조")
        res_col2.metric("요구되는 미래 매출", f"{req_future_rev/1_000_000_000_000:.1f}조")
        res_col3.metric(f"{sim_n_years}년 뒤 예상 TAM", f"{future_tam/1_000_000_000_000:.1f}조")
        
        share_diff = (implied_target_share * 100) - current_share
        delta_str = f"{share_diff:+.1f}%p 쟁탈 필요"
        res_col4.metric("내포된 요구 점유율", f"{implied_target_share*100:.1f}%", delta=delta_str, delta_color="inverse")
        
        with st.expander("🔍 역산 도출 과정 (수식 투명 공개)", expanded=True):
            st.markdown(
                f"""
                - **1단계 (요구 순이익)**: 목표 시가총액({target_future_mcap/1e12:.1f}조) ÷ 타겟 PER({sim_per:.1f}배) = **{req_future_ni/1e12:.1f}조 원**
                - **2단계 (요구 영업이익)**: 요구 순이익({req_future_ni/1e12:.1f}조) ÷ (1 - 유효세율 {tax_rate*100:.0f}%) = **{req_future_op/1e12:.1f}조 원**
                - **3단계 (요구 매출액)**: 요구 영업이익({req_future_op/1e12:.1f}조) ÷ 영업이익률({sim_opm*100:.1f}%) = **{req_future_rev/1e12:.1f}조 원**
                - **4단계 (요구 점유율)**: 요구 매출액({req_future_rev/1e12:.1f}조) ÷ 미래 글로벌 TAM({future_tam/1e12:.1f}조) = **{implied_target_share*100:.1f}%**
                """
            )
        
        st.info(
            f"**[가격표에 내포된 시장의 기대]**  \n"
            f"현재 시가총액({current_mcap/1_000_000_000_000:.1f}조)을 정당화하려면(목표수익률 {sim_target_return*100:.0f}%), "
            f"미래에 산업이 매년 {sim_tam_cagr*100:.1f}%씩 성장하고 회사가 {sim_opm*100:.1f}%의 마진을 낸다는 가정 하에 "
            f"멀티플이 {sim_per:.1f}배로 수축하더라도 **글로벌 파이의 {implied_target_share*100:.1f}%를 장악해야만 합니다.**  \n"
            f"👉 *현재 점유율({current_share:.1f}%) 대비 이 점유율을 달성하는 것이 현실적으로 가능한가요?*"
        )
def main() -> None:
    st.set_page_config(page_title="시장내포 가치분석", layout="wide")

    # === 사이드바: 종목 선택 ===
    st.sidebar.header("📊 종목 선택")
    available = _discover_tickers()
    if not available:
        st.error("data/valuation/ 폴더에 분석 가능한 종목 데이터가 없습니다. 파이프라인을 먼저 실행하세요.")
        st.stop()

    ticker_ids = [t[0] for t in available]
    ticker_labels = [t[1] for t in available]
    selected_idx = st.sidebar.selectbox(
        "분석할 종목",
        range(len(available)),
        format_func=lambda i: ticker_labels[i],
    )
    selected_ticker = ticker_ids[selected_idx]

    metrics_path = DATA_ROOT / selected_ticker / "normalized" / "metrics.json"
    market_path = DATA_ROOT / selected_ticker / "normalized" / "market.json"

    if not metrics_path.exists() or not market_path.exists():
        st.error(f"{selected_ticker} 종목의 정규화 데이터(metrics.json / market.json)가 없습니다.")
        st.stop()

    observations = load_metric_observations(metrics_path)
    market = load_market_data(market_path)
    input_set, checks, derived = run_audit(observations, market)
    all_observations = observations + derived

    company_name = market.get("company_name", selected_ticker)
    st.title(f"{company_name} 시장내포 가치분석")
    st.caption("출처와 검산, Reverse DCF, 가치 분해, 매출·마진, ROIC, 상대가치, CAP, 리스크, 내러티브, 종합 결론, Advanced 역산을 함께 봅니다.")

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
        tab_risk,
        tab_narrative,
        tab_synthesis,
        tab_peg,
        tab_tam,
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
            "9. 리스크",
            "10. 내러티브",
            "11. 종합 결론",
            "12. PEG 역산",
            "13. TAM 역산",
            "14. 공식",
            "15. 출처 상세",
        ]
    )

    with tab_audit:
        st.markdown("검산이 통과하지 않은 값은 다음 가치평가 렌즈로 넘기기 전에 확인합니다.")
        st.dataframe(_check_rows(checks), use_container_width=True, hide_index=True)

    with tab_inputs:
        st.markdown("같은 입력값을 Reverse DCF, Value Attribution, ROIC, 상대가치 렌즈가 공유합니다.")
        
        unique_periods = sorted(list({obs.period for obs in all_observations}), reverse=True)
        selected_periods = st.multiselect(
            "표시할 기간 선택", 
            options=unique_periods, 
            default=[unique_periods[0]] if unique_periods else None
        )
        
        filtered_observations = [obs for obs in all_observations if obs.period in selected_periods]
        st.dataframe(_observation_rows(filtered_observations), use_container_width=True, hide_index=True)

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

    with tab_risk:
        render_risk_downside_tab(input_set)

    with tab_narrative:
        render_narrative_tab(selected_ticker, company_name)

    with tab_synthesis:
        render_synthesis_tab(input_set)

    with tab_peg:
        render_peg_tab(input_set, market)

    with tab_tam:
        render_tam_tab(input_set, market)

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
            - `추정 EV = 정상화 FCF / (WACC - g)`
            - `괴리율 = (추정 EV - 현재 EV) / 현재 EV`
            """
        )
        st.warning("이 화면은 투자 권유가 아니라 다음 가치평가 단계로 넘길 입력값의 신뢰도를 확인하는 화면입니다.")

    with tab_source:
        st.markdown("데이터 출처 및 투명성")
        st.dataframe(pd.DataFrame([obs.dict() for obs in all_observations]))

    # === LLM Export & Save Sidebar ===
    st.sidebar.markdown("---")
    st.sidebar.header("📥 LLM Export")
    st.sidebar.caption("현재 화면에 분석된 모든 데이터와 내포 기대치 역산 결과를 다른 AI에 전달합니다.")

    # session_state를 일반 dict로 복사 (export_builder는 Streamlit 비의존)
    session_snapshot = {k: v for k, v in st.session_state.items() if k.startswith("export_")}
    # market_cap, net_income 등 export_builder가 참조하는 값 보충
    session_snapshot_inputs = dict(input_set.inputs)
    session_snapshot_inputs["market_cap"] = market.get("market_cap", 0)
    session_snapshot_inputs["net_income"] = input_set.inputs.get("net_income", 0)

    json_str = build_export_json(market, input_set.inputs)
    md_str = build_export_markdown(market, session_snapshot_inputs, session_snapshot)

    st.sidebar.download_button(
        label="📄 JSON 다운로드 (원본 데이터)",
        data=json_str,
        file_name=f"{market.get('ticker', 'ticker')}_valuation.json",
        mime="application/json",
    )
    st.sidebar.download_button(
        label="📝 Markdown 다운로드 (추천!)",
        data=md_str,
        file_name=f"{market.get('ticker', 'ticker')}_valuation.md",
        mime="text/markdown",
        help="원본 데이터는 물론 역산 분석 결과까지 담겨있어 다른 LLM에게 질문하기 가장 좋은 포맷입니다.",
    )

    # === 서버 측 자동 저장 ===
    st.sidebar.markdown("---")
    st.sidebar.header("📁 실시간 자동 저장")
    
    try:
        save_dir = save_analysis(market, session_snapshot_inputs, session_snapshot)
        st.sidebar.success(f"오늘자 분석 결과가 실시간 갱신되었습니다.\\n`{save_dir.relative_to(ROOT)}`")
    except Exception as e:
        st.sidebar.error(f"자동 저장 실패: {e}")

    # 과거 저장 이력 표시
    history = get_save_history(market)
    if history:
        st.sidebar.caption(f"이 종목의 저장 이력: {len(history)}일 (최근: {history[0]})")
    else:
        st.sidebar.caption("이 종목의 저장 이력이 없습니다.")

if __name__ == "__main__":
    main()
