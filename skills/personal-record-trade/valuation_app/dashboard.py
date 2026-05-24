from __future__ import annotations

from pathlib import Path

import streamlit as st

from valuation_app.audit import run_audit
from valuation_app.calculations import calc_required_fcf
from valuation_app.formatting import format_krw, format_ratio, source_label, status_label
from valuation_app.models import AuditCheck, MetricObservation, ValuationInputSet
from valuation_app.repository import load_market_data, load_metric_observations
from valuation_app.reverse_dcf import build_required_fcf_table, calc_normalized_fcf, required_fcf_multiple


ROOT = Path(__file__).resolve().parents[1]
METRICS_PATH = ROOT / "data/valuation/009150/normalized/metrics.json"
MARKET_PATH = ROOT / "data/valuation/009150/normalized/market.json"


def _display_value(obs: MetricObservation) -> str:
    if obs.unit == "ratio":
        return format_ratio(obs.value)
    return format_krw(obs.value)


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


def _reverse_dcf_rows(rows: list[dict[str, float | None]]) -> list[dict[str, str]]:
    formatted = []
    for row in rows:
        formatted.append(
            {
                "WACC": format_ratio(row["wacc"]),
                "영구성장률": format_ratio(row["terminal_growth"]),
                "필요 FCF": format_krw(row["required_fcf"]),
                "현재 FCF 대비": _format_multiple(row["current_fcf_multiple"]),
            }
        )
    return formatted


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


def render_source_panel(obs: MetricObservation) -> None:
    st.markdown(f"#### {obs.label}")
    st.write(f"값: **{_display_value(obs)}**")
    st.write(f"출처: **{source_label(obs.source_method)}**")
    st.write(f"기간: `{obs.period}`")
    st.write(f"보고서 코드: `{obs.report_code or '-'}`")
    st.write(f"재무제표: `{obs.statement_name or '-'}`")
    st.write(f"원문 계정명: `{obs.original_account_name or '-'}`")
    st.write(f"원문 금액: `{format_krw(obs.original_amount) if obs.original_amount is not None else '-'}`")
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
    sensitivity = build_required_fcf_table(
        enterprise_value=float(enterprise_value),
        current_fcf=current_fcf,
        wacc_values=[0.07, 0.08, 0.09, 0.10, 0.11],
        terminal_growth_values=[0.01, 0.02, 0.03, 0.04],
    )
    st.dataframe(_reverse_dcf_rows(sensitivity), use_container_width=True, hide_index=True)

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
    op_margin = s1.slider("정상화 영업이익률", min_value=0.0, max_value=25.0, value=latest_margin, step=0.5) / 100.0
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


def main() -> None:
    st.set_page_config(page_title="삼성전기 가치분석", layout="wide")
    st.title("삼성전기 시장내포 가치분석")
    st.caption("Phase 1-2: 출처와 검산을 확인한 뒤, 현재 EV가 요구하는 FCF를 Reverse DCF로 역산합니다.")

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

    tab_audit, tab_inputs, tab_reverse_dcf, tab_formula, tab_source = st.tabs(
        ["1. 검산", "2. 입력값", "3. Reverse DCF", "4. 공식", "5. 출처 상세"]
    )

    with tab_audit:
        st.markdown("검산이 통과하지 않은 값은 다음 가치평가 렌즈로 넘기기 전에 확인합니다.")
        st.dataframe(_check_rows(checks), use_container_width=True, hide_index=True)

    with tab_inputs:
        st.markdown("같은 입력값을 Reverse DCF, Value Attribution, ROIC, 상대가치 렌즈가 공유합니다.")
        st.dataframe(_observation_rows(all_observations), use_container_width=True, hide_index=True)

    with tab_reverse_dcf:
        render_reverse_dcf_tab(input_set)

    with tab_formula:
        st.markdown(
            """
            - `FCF = 영업활동현금흐름 - CAPEX`
            - `순부채 = 단기차입금 + 장기차입금 - 현금`
            - `EV = 시가총액 + 순부채`
            - `NOPAT = 영업이익 × (1 - 세율)`
            - `투하자본 = 자본총계 + 순부채`
            - `ROIC = NOPAT / 투하자본`
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
