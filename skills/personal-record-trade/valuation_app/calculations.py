from __future__ import annotations


def calc_fcf(op_cashflow: float, capex: float) -> float:
    """Free cash flow using capex as a positive outflow."""
    return op_cashflow - capex


def calc_net_debt(short_debt: float, long_debt: float, cash: float) -> float:
    return short_debt + long_debt - cash


def calc_enterprise_value(
    market_cap: float,
    net_debt: float,
    minority_interest: float = 0.0,
    non_operating_assets: float = 0.0,
) -> float:
    return market_cap + net_debt + minority_interest - non_operating_assets


def calc_nopat(operating_income: float, tax_rate: float) -> float:
    return operating_income * (1.0 - tax_rate)


def calc_invested_capital(total_equity: float, net_debt: float) -> float:
    return total_equity + net_debt


def calc_roic(nopat: float, invested_capital: float) -> float | None:
    if invested_capital == 0:
        return None
    return nopat / invested_capital


def calc_required_fcf(enterprise_value: float, wacc: float, terminal_growth: float) -> float:
    if wacc <= terminal_growth:
        raise ValueError("WACC must be greater than terminal growth.")
    return enterprise_value * (wacc - terminal_growth)
