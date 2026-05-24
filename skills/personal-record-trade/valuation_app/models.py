from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


SourceMethod = Literal[
    "dart_direct",
    "rule",
    "llm",
    "calculated",
    "market",
    "manual",
]

AuditStatus = Literal["pass", "warning", "fail", "manual_override"]

Number = int | float


class MetricObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric_key: str
    label: str
    value: Number | None
    unit: str = "KRW"
    period: str
    source_method: SourceMethod
    report_year: str | None = None
    report_code: str | None = None
    statement_name: str | None = None
    original_account_name: str | None = None
    original_amount: Number | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    note: str = ""


class AuditCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    check_key: str
    label: str
    formula: str
    expected_value: Number | None
    actual_value: Number | None
    tolerance: float = Field(ge=0.0)
    status: AuditStatus
    inputs: list[str]
    explanation: str


class ValuationInputSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticker: str
    company_name: str
    valuation_date: date
    inputs: dict[str, Number | None]
    observation_keys: dict[str, str]


class UserOverride(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric_key: str
    previous_value: Number | None
    new_value: Number | None
    reason: str
    changed_at: datetime
