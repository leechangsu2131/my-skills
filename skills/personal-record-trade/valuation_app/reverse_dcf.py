from __future__ import annotations

from valuation_app.calculations import calc_required_fcf


def required_fcf_multiple(required_fcf: float | int | None, current_fcf: float | int | None) -> float | None:
    if required_fcf is None or current_fcf is None or current_fcf == 0:
        return None
    return required_fcf / current_fcf


def build_required_fcf_table(
    enterprise_value: float | int,
    current_fcf: float | int | None,
    wacc_values: list[float],
    terminal_growth_values: list[float],
) -> list[dict[str, float | None]]:
    rows: list[dict[str, float | None]] = []
    for wacc in wacc_values:
        for terminal_growth in terminal_growth_values:
            try:
                required_fcf = calc_required_fcf(enterprise_value, wacc, terminal_growth)
            except ValueError:
                required_fcf = None
            rows.append(
                {
                    "wacc": wacc,
                    "terminal_growth": terminal_growth,
                    "required_fcf": required_fcf,
                    "current_fcf_multiple": required_fcf_multiple(required_fcf, current_fcf),
                }
            )
    return rows


def calc_normalized_fcf(
    revenue: float | int,
    operating_margin: float,
    tax_rate: float,
    fcf_conversion: float,
) -> float:
    return revenue * operating_margin * (1.0 - tax_rate) * fcf_conversion
