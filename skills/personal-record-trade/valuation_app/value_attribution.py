from __future__ import annotations


def calc_no_growth_value(nopat: float | int, wacc: float) -> float:
    if wacc <= 0:
        raise ValueError("WACC must be positive.")
    return nopat / wacc


def calc_future_expectation_value(enterprise_value: float | int, no_growth_value: float | int) -> float:
    return enterprise_value - no_growth_value


def calc_future_expectation_ratio(
    future_expectation_value: float | int | None,
    enterprise_value: float | int | None,
) -> float | None:
    if future_expectation_value is None or enterprise_value is None or enterprise_value == 0:
        return None
    return future_expectation_value / enterprise_value


def build_value_attribution_table(
    enterprise_value: float | int,
    nopat: float | int,
    wacc_values: list[float],
) -> list[dict[str, float | None]]:
    rows: list[dict[str, float | None]] = []
    for wacc in wacc_values:
        try:
            no_growth_value = calc_no_growth_value(nopat, wacc)
        except ValueError:
            no_growth_value = None

        future_value = (
            None if no_growth_value is None else calc_future_expectation_value(enterprise_value, no_growth_value)
        )
        rows.append(
            {
                "wacc": wacc,
                "no_growth_value": no_growth_value,
                "future_expectation_value": future_value,
                "future_expectation_ratio": calc_future_expectation_ratio(future_value, enterprise_value),
            }
        )
    return rows
