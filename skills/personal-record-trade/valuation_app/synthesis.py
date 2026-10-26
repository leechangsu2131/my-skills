from __future__ import annotations

from valuation_app.models import ValuationInputSet
from valuation_app.calculations import calc_required_fcf
from valuation_app.value_attribution import (
    calc_future_expectation_ratio,
    calc_future_expectation_value,
    calc_no_growth_value,
)


def evaluate_signals(
    input_set: ValuationInputSet,
    wacc_assumption: float = 0.09,
    terminal_growth: float = 0.03,
    market: dict | None = None,
    context: dict | None = None,
    assumptions: dict | None = None,
) -> list[dict[str, str | float | None]]:
    """입력 데이터(ValuationInputSet)를 평가하여 3가지 핵심 신호(수익성, 기대감, 효율성)를 추출합니다."""
    signals: list[dict[str, str | float | None]] = []

    enterprise_value = input_set.inputs.get("enterprise_value")
    nopat = input_set.inputs.get("nopat")
    current_fcf = input_set.inputs.get("fcf")
    roic = input_set.inputs.get("roic")
    market = market or {}
    context = context or {}
    assumptions = assumptions or {}

    # 1. 기대감 (Value Attribution)
    growth_ratio = None
    if enterprise_value is not None and enterprise_value > 0 and nopat is not None:
        try:
            no_growth = calc_no_growth_value(nopat, wacc_assumption)
            fut_val = calc_future_expectation_value(enterprise_value, no_growth)
            growth_ratio = calc_future_expectation_ratio(fut_val, enterprise_value)
            if growth_ratio is not None:
                if growth_ratio > 0.6:
                    status = "고성장 기대 (부담)"
                    interpretation = "현재 수익력보다 미래 성장에 대한 의존도가 매우 높습니다."
                elif growth_ratio < 0.2:
                    status = "저성장 기대 (여유)"
                    interpretation = "미래 성장에 대한 기대치가 낮아, 작은 호재에도 민감하게 반응할 수 있습니다."
                else:
                    status = "적정 성장 기대"
                    interpretation = "현재 수익력과 미래 성장이 균형을 이루고 있습니다."
                
                signals.append({
                    "분야": "미래 성장 기대감",
                    "핵심 수치": growth_ratio,
                    "수치 형태": "ratio",
                    "상태": status,
                    "해석": interpretation,
                })
        except ValueError:
            pass

    # 2. 수익성 부담 (Reverse DCF 배수)
    if enterprise_value is not None and current_fcf is not None and current_fcf > 0:
        try:
            req_fcf = calc_required_fcf(enterprise_value, wacc_assumption, terminal_growth)
            fcf_multiple = req_fcf / current_fcf
            
            if fcf_multiple > 10.0:
                status = "높은 턴어라운드 요구"
                interpretation = "현재 잉여현금흐름보다 가파른 개선(10배 이상)을 요구합니다."
            elif fcf_multiple > 2.0:
                status = "성장 요구"
                interpretation = "현재 대비 꾸준한 현금흐름 개선이 필요합니다."
            else:
                status = "현금흐름 여유"
                interpretation = "현재의 현금흐름 창출력만으로도 가격 정당화가 수월합니다."
                
            signals.append({
                "분야": "요구 현금흐름(FCF) 부담",
                "핵심 수치": fcf_multiple,
                "수치 형태": "multiple",
                "상태": status,
                "해석": interpretation,
            })
        except ValueError:
            pass

    # 3. 자본 효율성 (ROIC Spread)
    if roic is not None:
        spread = roic - wacc_assumption
        if spread > 0.05:
            status = "우수한 경제적 해자"
            interpretation = "자본비용(WACC)을 훌쩍 넘는 자본수익률(ROIC)로 가치를 창출 중입니다."
        elif spread > 0.0:
            status = "가치 창출 구간"
            interpretation = "초과 이익을 내고 있으나 경쟁 심화에 취약할 수 있습니다."
        else:
            status = "가치 파괴 구간"
            interpretation = "투하된 자본이 비용(WACC)만큼의 수익을 내지 못하고 있습니다. ROIC 개선 스토리가 필수적입니다."
            
        signals.append({
            "분야": "현재 자본 효율성(ROIC)",
            "핵심 수치": spread,
            "수치 형태": "ratio",
            "상태": status,
            "해석": interpretation,
        })

    # 4. PEG-implied earnings growth and multiple-contraction growth
    market_cap = market.get("market_cap")
    net_income = input_set.inputs.get("net_income")
    peg = assumptions.get("target_peg", 1.5)
    if market_cap and net_income and net_income > 0 and peg and peg > 0:
        current_per = market_cap / net_income
        peg_growth = current_per / peg / 100.0
        duration = max(1, int(assumptions.get("peg_duration", 5)))
        terminal_per = assumptions.get("peg_terminal_per") or context.get("normal_per") or market.get("historical_average_per") or 15.0
        target_return = assumptions.get("peg_target_return", 0.10)
        contraction_growth = ((current_per / terminal_per) ** (1 / duration)) * (1 + target_return) - 1 if terminal_per > 0 else None

        if peg_growth >= 0.30 or (contraction_growth is not None and contraction_growth >= 0.30):
            status = "높은 이익성장 요구"
            interpretation = "PER을 정당화하려면 높은 이익성장이 필요합니다. 특히 멀티플이 정상 수준으로 낮아질 때 필요한 성장률이 실현 가능한지 과거 성장과 사업 전망으로 확인해야 합니다."
        elif peg_growth >= 0.15 or (contraction_growth is not None and contraction_growth >= 0.15):
            status = "이익성장 검증 필요"
            interpretation = "PEG와 멀티플 수축 가정이 요구하는 성장률을 회사의 과거 실적, 산업 성장률, 재투자 여력과 비교해야 합니다."
        else:
            status = "PEG 성장 요구 완만"
            interpretation = "설정한 PEG와 정상 PER 가정에서 역산된 성장률은 상대적으로 낮습니다. PEG 자체가 적정가치를 보장하지는 않습니다."

        signals.append({
            "분야": "PEG 내포 이익성장률",
            "핵심 수치": peg_growth,
            "보조 수치": contraction_growth,
            "수치 형태": "ratio",
            "상태": status,
            "해석": interpretation,
        })

    # 5. TAM-implied future market share
    current_revenue = input_set.inputs.get("revenue")
    current_op_income = input_set.inputs.get("operating_income")
    years = max(1, int(assumptions.get("tam_duration", 5)))
    currency = market.get("currency", "KRW")
    scale_divider = 1_000_000_000 if currency in {"USD", "달러"} else 1_000_000_000_000
    current_tam = (context.get("tam_current") or 0) * scale_divider
    if current_tam <= 0:
        current_tam = market.get("current_tam") or 0
    tam_cagr = assumptions.get("tam_cagr", (context.get("tam_cagr") or 10.0) / 100.0)
    target_return = assumptions.get("tam_target_return", 0.0)
    target_opm = assumptions.get("tam_opm")
    if target_opm is None:
        target_opm = current_op_income / current_revenue if current_op_income and current_revenue else 0.10
    target_per = assumptions.get("tam_target_per") or context.get("normal_per") or market.get("historical_average_per") or 15.0
    tax_rate = input_set.inputs.get("tax_rate")
    tax_rate = tax_rate if tax_rate is not None else 0.22
    market_cap = market.get("market_cap")
    if market_cap and current_tam > 0 and target_per > 0 and target_opm > 0 and tax_rate < 1:
        target_future_market_cap = market_cap * ((1 + target_return) ** years)
        required_net_income = target_future_market_cap / target_per
        required_operating_income = required_net_income / (1 - tax_rate)
        required_revenue = required_operating_income / target_opm
        future_tam = current_tam * ((1 + tam_cagr) ** years)
        implied_share = required_revenue / future_tam
        if implied_share >= 1:
            status = "요구 점유율 100% 이상"
            interpretation = "설정한 TAM 성장률, 정상 PER, 목표 마진으로는 필요한 매출이 미래 시장 전체보다 큽니다. 현재 가격 또는 가정 조합을 다시 검토해야 합니다."
        elif implied_share >= 0.30:
            status = "높은 점유율 확대 요구"
            interpretation = "현재 가격을 설명하려면 해당 시장의 큰 비중을 차지해야 합니다. TAM 범위와 경쟁사의 점유율을 확인하세요."
        else:
            status = "점유율 가정 검증 필요"
            interpretation = "요구 점유율이 30% 미만이어도 실제 사업의 해당 시장 매출 비중과 경쟁 구도를 확인해야 합니다."

        signals.append({
            "분야": "TAM 내포 요구 점유율",
            "핵심 수치": implied_share,
            "보조 수치": float(years),
            "수치 형태": "ratio",
            "상태": status,
            "해석": interpretation,
        })

    return signals


def build_next_quarter_checklist() -> list[dict[str, str]]:
    """다음 실적 발표 시 확인해야 할 체크리스트를 반환합니다."""
    return [
        {
            "카테고리": "매출/마진",
            "확인 포인트": "전장용/서버용 MLCC 비중 확대로 인한 전사 영업이익률(OPM) 개선 여부",
            "판단 기준": "기대치(예: 11~15%) 상회 시 강한 Bull 시그널",
        },
        {
            "카테고리": "투자/FCF",
            "확인 포인트": "FC-BGA 등 대규모 CAPEX 종료에 따른 잉여현금흐름(FCF) 턴어라운드",
            "판단 기준": "순영업활동현금흐름이 CAPEX를 유의미하게 앞지르기 시작하는지",
        },
        {
            "카테고리": "ROIC",
            "확인 포인트": "베트남 기판 라인 수율 안정화 및 가동률 상승 여부",
            "판단 기준": "전사 투하자본회수율(ROIC)의 턴어라운드 신호(특히 기판 부문)",
        },
        {
            "카테고리": "내러티브",
            "확인 포인트": "AI/전장 스토리를 뒷받침하는 고객사 수주 잔고(Backlog) 증가 현황",
            "판단 기준": "단순 모바일/PC 사이클 회복이 아닌, 장기 공급 계약 가시화 여부",
        },
    ]


def build_synthesis_explanation() -> str:
    """초보자용 종합 결론 안내 문구"""
    return (
        "이 도구는 **'내일 주가가 오를까요?'**를 맞히는 마법 구슬이 아닙니다. "
        "대신, 시장이 현재 가격에 어떤 **'기대치(Expectation)'**를 숨겨두었는지 역산(Reverse)하여 보여줍니다.\n\n"
        "아래 종합 신호에서 '부담'이나 '가치 파괴'가 뜬다면 주가가 비싸다는 뜻일 수도 있지만, "
        "반대로 **시장이 그만큼 회사의 폭발적인 턴어라운드를 강력하게 믿고 있다**는 뜻이기도 합니다. "
        "다음 실적발표 때 회사가 그 거대한 기대를 충족시키는지, 아래 **체크리스트**를 통해 추적하세요."
    )
