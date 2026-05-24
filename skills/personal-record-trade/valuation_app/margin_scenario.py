from __future__ import annotations

from valuation_app.reverse_dcf import calc_normalized_fcf, required_fcf_multiple


def _fcf_denominator(revenue: float | int, tax_rate: float, fcf_conversion: float) -> float:
    return revenue * (1.0 - tax_rate) * fcf_conversion


def calc_required_operating_margin(
    required_fcf: float | int,
    revenue: float | int,
    tax_rate: float,
    fcf_conversion: float,
) -> float | None:
    denominator = _fcf_denominator(revenue, tax_rate, fcf_conversion)
    if denominator <= 0:
        return None
    return required_fcf / denominator


def calc_required_revenue(
    required_fcf: float | int,
    operating_margin: float,
    tax_rate: float,
    fcf_conversion: float,
) -> float | None:
    denominator = operating_margin * (1.0 - tax_rate) * fcf_conversion
    if denominator <= 0:
        return None
    return required_fcf / denominator


def build_required_margin_table(
    base_revenue: float | int,
    required_fcf: float | int,
    growth_rates: list[float],
    tax_rate: float,
    fcf_conversion: float,
) -> list[dict[str, float | None]]:
    rows: list[dict[str, float | None]] = []
    for growth_rate in growth_rates:
        scenario_revenue = base_revenue * (1.0 + growth_rate)
        rows.append(
            {
                "growth_rate": growth_rate,
                "scenario_revenue": scenario_revenue,
                "required_operating_margin": calc_required_operating_margin(
                    required_fcf, scenario_revenue, tax_rate, fcf_conversion
                ),
            }
        )
    return rows


def build_margin_scenario_matrix(
    base_revenue: float | int,
    required_fcf: float | int,
    growth_rates: list[float],
    operating_margins: list[float],
    tax_rate: float,
    fcf_conversion: float,
) -> list[dict[float | str, float | None]]:
    rows: list[dict[float | str, float | None]] = []
    for growth_rate in growth_rates:
        scenario_revenue = base_revenue * (1.0 + growth_rate)
        row: dict[float | str, float | None] = {"growth_rate": growth_rate}
        for operating_margin in operating_margins:
            normalized_fcf = calc_normalized_fcf(scenario_revenue, operating_margin, tax_rate, fcf_conversion)
            row[operating_margin] = required_fcf_multiple(normalized_fcf, required_fcf)
        rows.append(row)
    return rows
