from __future__ import annotations


def format_krw(value: float | int | None) -> str:
    if value is None:
        return "-"
    sign = "-" if value < 0 else ""
    abs_value = abs(value)
    if abs_value >= 1_000_000_000_000:
        return f"{sign}{abs_value / 1_000_000_000_000:.1f}조원"
    return f"{sign}{abs_value / 100_000_000:,.0f}억원"


def format_ratio(value: float | int | None) -> str:
    if value is None:
        return "-"
    return f"{value * 100:.1f}%"


def status_label(status: str) -> str:
    labels = {
        "pass": "통과",
        "warning": "확인 필요",
        "fail": "실패",
        "manual_override": "수동 수정",
    }
    return labels.get(status, status)


def source_label(source_method: str) -> str:
    labels = {
        "dart_direct": "DART",
        "rule": "RULE",
        "llm": "LLM",
        "calculated": "CALC",
        "market": "MARKET",
        "manual": "MANUAL",
    }
    return labels.get(source_method, source_method.upper())
