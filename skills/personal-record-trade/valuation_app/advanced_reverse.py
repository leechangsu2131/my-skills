from __future__ import annotations


def calc_implied_expected_return(enterprise_value: float, fcf: float, long_term_growth: float) -> float | None:
    """
    현재 기업가치(EV)와 잉여현금흐름(FCF)을 바탕으로, 시장이 내포하고 있는 기대수익률(Implied Expected Return)을 역산합니다.
    공식: Implied Return = FCF Yield + Long-term Growth = (FCF / EV) + g
    
    Args:
        enterprise_value: 기업가치 (예: 시가총액 + 순부채)
        fcf: 최근 1년 또는 정상화된 잉여현금흐름
        long_term_growth: 장기 예상 영구성장률 (예: 3% -> 0.03)
        
    Returns:
        float: 시장의 내포 기대수익률 (예: 8% -> 0.08)
    """
    if enterprise_value <= 0:
        return None
        
    fcf_yield = fcf / enterprise_value
    return fcf_yield + long_term_growth


def calc_implied_growth_from_peg(per: float, target_peg: float) -> float | None:
    """
    PEG(Price/Earnings to Growth) 비율을 기반으로 내포된 이익 성장률을 역산합니다.
    PEG = PER / (Growth * 100)
    따라서 Growth = PER / target_peg / 100
    
    Args:
        per: 현재 주가수익비율 (예: 20.0)
        target_peg: 적정하다고 가정하는 PEG 배수 (예: 1.0, 1.5)
        
    Returns:
        float: 시장이 내포하고 있는 연평균 이익 성장률(소수점 비율, 예: 20% -> 0.2)
    """
    if target_peg <= 0 or per <= 0:
        return None
    
    implied_growth_pct = per / target_peg
    return implied_growth_pct / 100.0


def calc_implied_market_share(required_revenue: float, estimated_tam: float) -> float | None:
    """
    Reverse DCF에서 요구되는 매출을 달성하기 위해, 전체 TAM 중 몇 %의 점유율을 차지해야 하는지 역산합니다.
    
    Args:
        required_revenue: 현재 주가를 정당화하기 위해 요구되는 타겟 연도 매출액
        estimated_tam: 타겟 연도의 전체 시장(Total Addressable Market) 규모 예측치
        
    Returns:
        float: 요구되는 시장 점유율 비율 (예: 30% -> 0.3)
    """
    if estimated_tam <= 0 or required_revenue < 0:
        return None
        
    return required_revenue / estimated_tam


def decompose_expected_return(
    dividend_yield: float, earnings_growth: float, multiple_expansion: float
) -> dict[str, float]:
    """
    기대수익률을 세 가지 원천(배당, 이익성장, 멀티플 팽창)으로 분해하여 총 기대수익률을 계산합니다.
    
    Args:
        dividend_yield: 예상 배당수익률 (예: 2% -> 0.02)
        earnings_growth: 연평균 예상 이익 성장률 (예: 8% -> 0.08)
        multiple_expansion: 보유 기간 동안 PER 등 멀티플의 연평균 팽창률 (예: 5% 상승 -> 0.05)
        
    Returns:
        dict: 각 구성요소와 총 기대수익률(Total Expected Return)을 담은 딕셔너리
    """
    total_return = dividend_yield + earnings_growth + multiple_expansion
    
    return {
        "dividend_yield": dividend_yield,
        "earnings_growth": earnings_growth,
        "multiple_expansion": multiple_expansion,
        "total_expected_return": total_return
    }
