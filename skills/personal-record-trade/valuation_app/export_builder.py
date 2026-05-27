"""Export builder: 분석 결과를 Markdown / JSON 문자열로 조립하는 순수 함수 모듈.

dashboard.py의 인라인 빌드 로직을 추출하여,
사이드바 다운로드 버튼과 서버 저장 기능이 동일한 함수를 공유하도록 합니다.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any


def build_export_json(market: dict[str, Any], inputs: dict[str, Any]) -> str:
    """원본 시장 데이터 + 재무 입력값을 JSON 문자열로 반환."""
    export_dict = {
        "export_timestamp": datetime.now().isoformat(),
        "market_data": market,
        "financial_inputs": inputs,
    }
    return json.dumps(export_dict, ensure_ascii=False, indent=2, default=str)


def build_export_markdown(
    market: dict[str, Any],
    inputs: dict[str, Any],
    session: dict[str, Any],
) -> str:
    """수식 / 가정 / 역산 결과가 모두 담긴 Markdown 문자열을 반환.

    Parameters
    ----------
    market : dict
        ``load_market_data()`` 결과.
    inputs : dict
        ``ValuationInputSet.inputs``.
    session : dict
        ``st.session_state`` 를 dict 로 복사한 것.
        Streamlit 의존성을 제거하여 단위 테스트가 가능하도록 합니다.
    """
    ticker = market.get("ticker", "ticker")
    company = market.get("company_name", "Company")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")

    md = f"""# {company} ({ticker}) 시장 내포 가치 역산(Reverse Engineering) 데이터
> 분석 시점: {ts}

당신은 최고 수준의 가치평가 전문가입니다. 아래 데이터를 바탕으로, 이 기업의 '현재 주가'에 선반영된 시장의 엄청난 기대를 짚어내고 그것이 현실적인지 비판적으로 토론해 주세요.

## 1. 시장 데이터 (Market Data)
- **현재 시가총액**: {market.get('market_cap', 0):,} 원
- **현재 주가**: {market.get('price', 0):,} 원
- **과거 평균 PER**: {market.get('historical_average_per', 15.0)} 배
- **Peer 평균 PER**: {market.get('peer_average_per', 15.0)} 배
- **현재 글로벌 TAM**: {market.get('current_tam', 0):,} 원
- **5년 뒤 예측 TAM**: {market.get('projected_tam_5yr', 0):,} 원
- **시장 데이터 기준일**: {market.get('market_data_as_of', '-')}

## 2. 주요 재무 입력값 (Financial Inputs)
"""
    for k, v in inputs.items():
        if isinstance(v, (int, float)):
            md += f"- **{k}**: {v:,}\n"
        else:
            md += f"- **{k}**: {v}\n"

    md += "\n## 3. 내포 기대치 역산 결과 (Implied Market Expectations)\n"
    md += _section_peg(session, inputs)
    md += _section_tam(session)
    md += _section_reverse_dcf(session, inputs)
    md += _section_value_attribution(session, inputs)
    md += _section_implied_roic(session, inputs)
    md += _section_cap(session)

    md += "\n---\n"
    md += (
        "> 이 문서는 Reverse Engineering Valuation Dashboard에서 자동 생성되었습니다. "
        "각 섹션의 **수식**과 **입력 가정**을 근거로, 현재 주가에 내포된 시장 기대의 현실성을 "
        "비판적으로 검토해 주세요.\n"
    )

    return md


# ── 내부 헬퍼: 각 렌즈별 마크다운 섹션 ──────────────────────────


def _section_peg(session: dict, inputs: dict) -> str:
    peg_g = session.get("export_peg_implied_g")
    if peg_g is None:
        return ""
    peg_n = session.get("export_peg_n_years", 5)
    peg_per = session.get("export_peg_terminal_per", 15.0)

    mc = inputs.get("market_cap") or 0
    ni = inputs.get("net_income") or 1
    per_actual = mc / ni if ni else 0

    s = "### A. 성장성 — PEG 멀티플 수축 방어\n"
    s += f"- **수식**: `요구 성장률 = [ (현재 PER ÷ 미래 정상 PER)^(1/n) × (1 + 목표 수익률) ] - 1`\n"
    s += f"- **입력 가정**: 현재 PER = {per_actual:.1f}배, 투자기간(n) = {peg_n}년, 미래 정상 PER = {peg_per:.1f}배\n"
    s += (
        f"- **역산 결과**: 현재 시가총액에 진입한 투자자가 손해를 보지 않으려면, "
        f"회사는 향후 {peg_n}년 동안 **매년 연평균 {peg_g*100:.1f}%씩** 이익이 복리로 성장해야 함.\n\n"
    )
    return s


def _section_tam(session: dict) -> str:
    tam_share = session.get("export_tam_implied_share")
    if tam_share is None:
        return ""
    tam_n = session.get("export_tam_n_years", 5)
    tam_cagr = session.get("export_tam_cagr", 0.1)
    tam_ret = session.get("export_tam_target_return", 0.0)
    tam_opm = session.get("export_tam_opm", 0.10)
    tam_per = session.get("export_tam_per", 15.0)

    s = "### B. 시장 점유율 — TAM 파이 쟁탈전\n"
    s += (
        "- **수식**: `요구 점유율 = 요구 매출 ÷ 미래 TAM`\n"
        "  - `요구 매출 = 요구 영업이익 ÷ OPM`\n"
        "  - `요구 영업이익 = 요구 순이익 ÷ (1 - 유효세율)`\n"
        "  - `요구 순이익 = 목표 미래 시가총액 ÷ 타겟 PER`\n"
        "  - `목표 미래 시가총액 = 현재 시가총액 × (1 + 목표수익률)^n`\n"
    )
    s += (
        f"- **입력 가정**: 투자기간 = {tam_n}년, TAM 연성장률 = {tam_cagr*100:.1f}%, "
        f"목표 수익률 = {tam_ret*100:.1f}%, 미래 OPM = {tam_opm*100:.1f}%, 타겟 PER = {tam_per:.1f}배\n"
    )
    s += (
        f"- **역산 결과**: 이 시나리오 하에서 목표 수익률을 달성하려면 "
        f"회사는 미래 글로벌 시장의 **{tam_share*100:.1f}%**를 장악해야 함.\n\n"
    )
    return s


def _section_reverse_dcf(session: dict, inputs: dict) -> str:
    req_fcf = session.get("export_req_fcf")
    if req_fcf is None:
        return ""
    dcf_wacc = session.get("export_dcf_wacc", 0.09)
    dcf_g = session.get("export_dcf_terminal_g", 0.03)
    ev_val = inputs.get("enterprise_value", 0)
    cur_fcf = inputs.get("fcf", 0)
    multiple = req_fcf / cur_fcf if cur_fcf else None

    s = "### C. 현금창출력 — Reverse DCF\n"
    s += f"- **수식**: `요구 FCF = 기업가치(EV) × (WACC - 영구성장률)`\n"
    s += (
        f"- **입력 가정**: EV = {ev_val/1e12:.2f}조 원, "
        f"WACC = {dcf_wacc*100:.1f}%, 영구성장률(g) = {dcf_g*100:.1f}%\n"
    )
    s += (
        f"- **역산 결과**: 현재 기업가치를 정당화하기 위해 내년부터 창출해야 할 "
        f"**요구 FCF는 {req_fcf/1e12:.2f}조 원** "
    )
    if multiple is not None:
        s += f"(현재 FCF {cur_fcf/1e12:.2f}조의 **{multiple:.1f}배**)"
    s += ".\n\n"
    return s


def _section_value_attribution(session: dict, inputs: dict) -> str:
    future_value = session.get("export_future_value")
    if future_value is None:
        return ""
    ev_val = inputs.get("enterprise_value", 0)
    nopat_val = inputs.get("nopat", 0)
    ratio = future_value / ev_val * 100 if ev_val else 0

    s = "### D. 가치 분해 — Value Attribution\n"
    s += f"- **수식**: `초과가치(미래 기대감) = EV - (현재 NOPAT ÷ WACC)`\n"
    s += (
        f"- **입력 가정**: EV = {ev_val/1e12:.2f}조 원, "
        f"NOPAT = {nopat_val/1e12:.2f}조 원\n"
    )
    s += (
        f"- **역산 결과**: 현재 기업가치 중 '순수 미래 성장 기대감'으로 형성된 초과가치는 "
        f"**{future_value/1e12:.2f}조 원** (전체의 **{ratio:.1f}%**).\n\n"
    )
    return s


def _section_implied_roic(session: dict, inputs: dict) -> str:
    implied_roic = session.get("export_implied_roic")
    if implied_roic is None:
        return ""
    ic_val = inputs.get("invested_capital", 0)
    cur_roic = inputs.get("roic", 0)
    roic_multiple = implied_roic / cur_roic if cur_roic else None

    s = "### E. 자본 효율성 — Implied ROIC\n"
    s += (
        "- **수식**: `미래 ROIC = (EV × (WACC-g) + NOPAT) / IC` "
        "(현재 기업가치를 성장률 공식에 대입하여 역산)\n"
    )
    s += f"- **입력 가정**: 투하자본(IC) = {ic_val/1e12:.2f}조 원, 현재 ROIC = {cur_roic*100:.1f}%\n"
    s += (
        f"- **역산 결과**: 현재 밸류에이션을 유지하며 성장하려면 향후 ROIC는 "
        f"**{implied_roic*100:.1f}%** 수준이어야 함"
    )
    if roic_multiple is not None:
        s += f" (현재의 **{roic_multiple:.1f}배**)"
    s += ".\n\n"
    return s


def _section_cap(session: dict) -> str:
    cap = session.get("export_discounted_cap")
    if cap is None:
        return ""
    cap_roic = session.get("export_cap_roic", 0.1)
    future_val = session.get("export_future_value", 0)

    s = "### F. 초과수익 지속기간 — CAP\n"
    s += (
        "- **수식**: `요구 CAP = 초과가치가 연간 경제적 이익(EP)의 할인 현가 합과 "
        "일치하는 기간(n년)`\n"
        "  - `EP = 투하자본 × (ROIC - WACC)`\n"
    )
    s += (
        f"- **입력 가정**: 정상화 ROIC = {cap_roic*100:.1f}%, "
        f"회수해야 할 초과가치 = {future_val/1e12:.2f}조 원\n"
    )
    s += (
        f"- **역산 결과**: 이 수익성으로 초과가치를 모두 회수하려면 "
        f"독점적 초과이익 상태를 **{cap:.1f}년** 동안 연속 유지해야 함.\n\n"
    )
    return s
