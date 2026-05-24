from __future__ import annotations

from pathlib import Path

import streamlit as st

from valuation_app.audit import run_audit
from valuation_app.formatting import format_krw, format_ratio, source_label, status_label
from valuation_app.models import AuditCheck, MetricObservation
from valuation_app.repository import load_market_data, load_metric_observations


ROOT = Path(__file__).resolve().parents[1]
METRICS_PATH = ROOT / "data/valuation/009150/normalized/metrics.json"
MARKET_PATH = ROOT / "data/valuation/009150/normalized/market.json"


def _metric_map(observations: list[MetricObservation]) -> dict[str, MetricObservation]:
    return {obs.metric_key: obs for obs in observations}


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


def main() -> None:
    st.set_page_config(page_title="삼성전기 가치분석", layout="wide")
    st.title("삼성전기 시장내포 가치분석")
    st.caption("Phase 1: 결론 전에 출처, 공식, 검산부터 확인합니다.")

    observations = load_metric_observations(METRICS_PATH)
    market = load_market_data(MARKET_PATH)
    input_set, checks, derived = run_audit(observations, market)
    all_observations = observations + derived
    metrics = _metric_map(all_observations)

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

    tab_audit, tab_inputs, tab_formula, tab_source = st.tabs(
        ["1. 검산", "2. 입력값", "3. 공식", "4. 출처 상세"]
    )

    with tab_audit:
        st.markdown("검산이 통과하지 않은 값은 다음 가치평가 렌즈로 넘기기 전에 확인합니다.")
        st.dataframe(_check_rows(checks), use_container_width=True, hide_index=True)

    with tab_inputs:
        st.markdown("같은 입력값을 Reverse DCF, Value Attribution, ROIC, 상대가치 렌즈가 공유합니다.")
        st.dataframe(_observation_rows(all_observations), use_container_width=True, hide_index=True)

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
