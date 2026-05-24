from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


SourceMethod = Literal[
    "dart_direct",
    "rule",
    "llm",
    "calculated",
    "market",
    "manual",
]

AuditStatus = Literal["pass", "warning", "fail", "manual_override"]


class MetricObservation(BaseModel):
    metric_key: str
    label: str
    value: float | None
    unit: str = "KRW"
    period: str
    source_method: SourceMethod
    report_year: str | None = None
    report_code: str | None = None
    statement_name: str | None = None
    original_account_name: str | None = None
    original_amount: float | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    note: str = ""


class AuditCheck(BaseModel):
    check_key: str
    label: str
    formula: str
    expected_value: float | None
    actual_value: float | None
    tolerance: float
    status: AuditStatus
    inputs: list[str]
    explanation: str


class ValuationInputSet(BaseModel):
    ticker: str
    company_name: str
    valuation_date: str
    inputs: dict[str, float | None]
    observation_keys: dict[str, str]


class UserOverride(BaseModel):
    metric_key: str
    previous_value: float | None
    new_value: float | None
    reason: str
    changed_at: str
