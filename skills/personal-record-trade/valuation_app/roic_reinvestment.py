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
