from __future__ import annotations

import math


def calc_annual_economic_profit_from_roic(
    invested_capital: float | int | None,
    roic: float | int | None,
    wacc: float,
) -> float | None:
    if invested_capital is None or roic is None or invested_capital <= 0:
        return None
    return float(invested_capital) * (float(roic) - wacc)


def calc_discounted_economic_profit_value(
    annual_economic_profit: float | int | None,
    wacc: float,
    years: int,
) -> float | None:
    if annual_economic_profit is None or annual_economic_profit <= 0 or wacc <= 0 or years <= 0:
        return None
    annuity_factor = (1 - (1 + wacc) ** (-years)) / wacc
    return float(annual_economic_profit) * annuity_factor


def calc_simple_payback_years(
    excess_value: float | int | None,
    annual_economic_profit: float | int | None,
) -> float | None:
    if excess_value is None or annual_economic_profit is None or excess_value <= 0 or annual_economic_profit <= 0:
        return None
    return float(excess_value) / float(annual_economic_profit)


def calc_discounted_cap_years(
    excess_value: float | int | None,
    annual_economic_profit: float | int | None,
    wacc: float,
) -> float | None:
    if excess_value is None or annual_economic_profit is None or excess_value <= 0 or annual_economic_profit <= 0:
        return None
    if wacc <= 0:
        return None

    perpetuity_value = float(annual_economic_profit) / wacc
    if perpetuity_value <= float(excess_value):
        return None

    remaining_fraction = 1 - (float(excess_value) * wacc / float(annual_economic_profit))
    if remaining_fraction <= 0:
        return None
    return -math.log(remaining_fraction) / math.log(1 + wacc)


def build_cap_duration_table(
    excess_value: float | int,
    invested_capital: float | int,
    roic_values: list[float],
    wacc: float,
    periods: list[int],
) -> list[dict[float | str, float | None]]:
    rows: list[dict[float | str, float | None]] = []
    for roic in roic_values:
        annual_economic_profit = calc_annual_economic_profit_from_roic(invested_capital, roic, wacc)
        row: dict[float | str, float | None] = {
            "roic": roic,
            "annual_economic_profit": annual_economic_profit,
            "simple_payback_years": calc_simple_payback_years(excess_value, annual_economic_profit),
            "discounted_cap_years": calc_discounted_cap_years(excess_value, annual_economic_profit, wacc),
        }
        for years in periods:
            row[years] = calc_discounted_economic_profit_value(annual_economic_profit, wacc, years)
        rows.append(row)
    return rows


def build_cap_metric_explanations() -> list[dict[str, str]]:
    return [
        {
            "지표": "초과가치",
            "무슨 뜻인가": "현재 EV에서 현재 수익력만 자본화한 가치를 뺀 금액입니다.",
            "어떻게 읽나": "이 값이 클수록 현재 주가는 미래 이익 개선이나 긴 경쟁우위에 더 많이 기대고 있습니다.",
        },
        {
            "지표": "연간 경제적 이익",
            "무슨 뜻인가": "선택한 ROIC가 WACC를 넘는 만큼 투하자본이 매년 만드는 초과이익입니다.",
            "어떻게 읽나": "음수면 현재 또는 선택한 ROIC가 자본비용을 넘지 못해 경쟁우위 기간을 계산할 출발점이 없습니다.",
        },
        {
            "지표": "단순 회수 CAP",
            "무슨 뜻인가": "할인을 무시하고 초과가치를 연간 경제적 이익으로 나눈 기간입니다.",
            "어떻게 읽나": "직관용 숫자입니다. 실제 가치평가에서는 돈의 시간가치를 반영한 할인 CAP도 함께 봐야 합니다.",
        },
        {
            "지표": "할인 CAP",
            "무슨 뜻인가": "연간 경제적 이익을 WACC로 할인했을 때 초과가치를 설명하는 데 필요한 기간입니다.",
            "어떻게 읽나": "불가능으로 나오면 그 ROIC가 영구히 지속되어도 현재 초과가치를 설명하지 못한다는 뜻입니다.",
        },
    ]
