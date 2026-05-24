from __future__ import annotations


def calc_ev_nopat_multiple(enterprise_value: float | int, nopat: float | int | None) -> float | None:
    if nopat is None or nopat <= 0:
        return None
    return enterprise_value / nopat


def calc_implied_roic_from_value_driver(
    ev_nopat_multiple: float | int | None,
    wacc: float,
    growth_rate: float,
) -> float | None:
    if ev_nopat_multiple is None or wacc <= growth_rate:
        return None
    denominator = 1.0 - (wacc - growth_rate) * ev_nopat_multiple
    if denominator <= 0:
        return None
    return growth_rate / denominator


def calc_max_ev_nopat_multiple(wacc: float, growth_rate: float) -> float | None:
    if wacc <= growth_rate:
        return None
    return 1.0 / (wacc - growth_rate)


def calc_implied_future_roic_from_invested_capital(
    enterprise_value: float | int,
    invested_capital: float | int | None,
    wacc: float,
    growth_rate: float,
) -> float | None:
    if invested_capital is None or invested_capital <= 0 or wacc <= growth_rate:
        return None
    return growth_rate + enterprise_value * (wacc - growth_rate) / invested_capital


def calc_reinvestment_rate(growth_rate: float, roic: float | int | None) -> float | None:
    if roic is None or roic <= 0:
        return None
    return growth_rate / roic


def calc_growth_from_reinvestment(roic: float, reinvestment_rate: float) -> float:
    return roic * reinvestment_rate


def calc_economic_profit(nopat: float | int, invested_capital: float | int, wacc: float) -> float:
    return nopat - invested_capital * wacc


def build_reinvestment_matrix(
    growth_rates: list[float],
    roic_values: list[float],
) -> list[dict[float | str, float | None]]:
    rows: list[dict[float | str, float | None]] = []
    for growth_rate in growth_rates:
        row: dict[float | str, float | None] = {"growth_rate": growth_rate}
        for roic in roic_values:
            row[roic] = calc_reinvestment_rate(growth_rate, roic)
        rows.append(row)
    return rows


def build_roic_metric_explanations() -> list[dict[str, str]]:
    return [
        {
            "지표": "현재 ROIC",
            "무슨 뜻인가": "현재 사업 수익성입니다. 투하자본 100원을 넣어 세후 영업이익을 몇 원 벌었는지 봅니다.",
            "어떻게 읽나": "WACC보다 높으면 현재 사업이 자본비용을 이기고, 낮으면 현재 수익력은 아직 부족합니다.",
        },
        {
            "지표": "WACC 대비",
            "무슨 뜻인가": "현재 ROIC와 요구수익률의 차이입니다.",
            "어떻게 읽나": "음수면 현재 사업 수익성이 투자자가 요구하는 수익률보다 낮다는 뜻입니다.",
        },
        {
            "지표": "경제적 이익",
            "무슨 뜻인가": "NOPAT에서 투하자본에 대한 자본비용을 뺀 값입니다.",
            "어떻게 읽나": "음수면 회계상 이익은 있어도 자본비용까지 보상하면 부족하다는 뜻입니다.",
        },
        {
            "지표": "EV/NOPAT",
            "무슨 뜻인가": "현재 기업가치가 현재 세후영업이익의 몇 배인지 봅니다.",
            "어떻게 읽나": "배수가 높을수록 현재 이익보다 미래 이익 개선에 더 많이 기대고 있다는 뜻입니다.",
        },
        {
            "지표": "현재 NOPAT 기준 역산",
            "무슨 뜻인가": "현재 NOPAT을 고정한 채 EV/NOPAT 공식으로 ROIC를 역산한 값입니다.",
            "어떻게 읽나": "해가 안 나옵니다는 현재 이익 기준 단순 공식으로는 현재 주가를 설명할 수 없다는 뜻입니다.",
        },
        {
            "지표": "1단계 공식 최대 EV/NOPAT",
            "무슨 뜻인가": "선택한 WACC와 성장률에서 단순 1단계 공식이 설명할 수 있는 이론상 최대 배수입니다.",
            "어떻게 읽나": "현재 EV/NOPAT이 이 값보다 크면 단순 공식이 아니라 정상화 이익, 긴 성장 기간, 경쟁우위 기간을 봐야 합니다.",
        },
        {
            "지표": "주가 내포 미래 ROIC",
            "무슨 뜻인가": "현재 EV를 투하자본 기준으로 맞추려면 미래 ROIC가 얼마여야 하는지 역산한 값입니다.",
            "어떻게 읽나": "이 숫자를 억지로 설명하려면 그만큼 큰 폭의 마진 개선, 고부가 믹스, 또는 장기 경쟁우위가 필요하다는 뜻입니다.",
        },
        {
            "지표": "현재 대비 미래 ROIC 배수",
            "무슨 뜻인가": "주가 내포 미래 ROIC가 현재 ROIC의 몇 배인지 봅니다.",
            "어떻게 읽나": "배수가 높을수록 시장이 요구하는 수익성 개선 폭이 큽니다.",
        },
    ]
