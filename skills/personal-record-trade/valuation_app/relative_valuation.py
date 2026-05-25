from __future__ import annotations


def _safe_multiple(numerator: float | int | None, denominator: float | int | None) -> float | None:
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return numerator / denominator


def calc_price_to_book(market_cap: float | int | None, total_equity: float | int | None) -> float | None:
    return _safe_multiple(market_cap, total_equity)


def calc_price_to_earnings(market_cap: float | int | None, net_income: float | int | None) -> float | None:
    return _safe_multiple(market_cap, net_income)


def calc_pe_from_eps(price: float | int | None, eps: float | int | None) -> float | None:
    return _safe_multiple(price, eps)


def calc_ev_to_sales(enterprise_value: float | int | None, revenue: float | int | None) -> float | None:
    return _safe_multiple(enterprise_value, revenue)


def calc_ev_to_nopat(enterprise_value: float | int | None, nopat: float | int | None) -> float | None:
    return _safe_multiple(enterprise_value, nopat)


def calc_implied_roe_from_pb(
    price_to_book: float | int | None,
    required_return: float,
    growth_rate: float,
) -> float | None:
    if price_to_book is None or required_return <= growth_rate:
        return None
    return growth_rate + price_to_book * (required_return - growth_rate)


def calc_implied_nopat_margin_from_ev_sales(
    ev_sales: float | int | None,
    wacc: float,
    growth_rate: float,
    roic: float,
) -> float | None:
    if ev_sales is None or wacc <= growth_rate or roic <= growth_rate:
        return None
    reinvestment_drag = 1.0 - growth_rate / roic
    denominator = reinvestment_drag * (1.0 + growth_rate)
    if denominator <= 0:
        return None
    return ev_sales * (wacc - growth_rate) / denominator


def calc_implied_operating_margin_from_ev_sales(
    ev_sales: float | int | None,
    wacc: float,
    growth_rate: float,
    roic: float,
    tax_rate: float,
) -> float | None:
    nopat_margin = calc_implied_nopat_margin_from_ev_sales(ev_sales, wacc, growth_rate, roic)
    tax_factor = 1.0 - tax_rate
    if nopat_margin is None or tax_factor <= 0:
        return None
    return nopat_margin / tax_factor


def build_relative_metric_explanations() -> list[dict[str, str]]:
    return [
        {
            "지표": "P/E",
            "무슨 뜻인가": "시가총액이 순이익의 몇 배인지 보는 지표입니다.",
            "어떻게 읽나": "PER이 높을수록 현재 순이익보다 미래 이익 증가에 더 많이 기대고 있다는 뜻입니다.",
        },
        {
            "지표": "P/B",
            "무슨 뜻인가": "시가총액이 장부상 자본총계의 몇 배인지 봅니다.",
            "어떻게 읽나": "P/B가 높을수록 시장은 높은 내포 ROE 또는 긴 초과수익 기간을 요구합니다.",
        },
        {
            "지표": "EV/Sales",
            "무슨 뜻인가": "기업가치가 매출의 몇 배인지 봅니다.",
            "어떻게 읽나": "매출 1원당 높은 값을 주고 있다면, 그 가격을 설명할 필요 마진과 재투자 효율을 역산해야 합니다.",
        },
        {
            "지표": "EV/NOPAT",
            "무슨 뜻인가": "기업가치가 현재 세후영업이익의 몇 배인지 봅니다.",
            "어떻게 읽나": "배수가 높을수록 현재 이익보다 미래 정상화 이익에 기대고 있다는 뜻입니다.",
        },
    ]
