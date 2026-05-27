# Samsung Electro-Mechanics Data Integrity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Phase 1 of the Samsung Electro-Mechanics valuation tool: a local data integrity dashboard that shows annual and latest-quarter inputs, source lineage, and core valuation input checks before any valuation conclusion.

**Architecture:** Add a small Python package, `valuation_app`, beside the existing Google Sheets automation scripts. The package separates data models, calculations, repository loading, audit checks, formatting, and a Streamlit dashboard so each piece can be tested independently.

**Tech Stack:** Python 3, Pydantic v2, pytest, Streamlit, local JSON seed data, optional future DART/LLM adapters.

---

## Scope Check

This plan implements only Phase 1 from the approved spec: Samsung Electro-Mechanics data integrity. It does not implement Reverse DCF screens, ROIC/CAP lenses, Google Sheets export, or live DART API calls. Those become separate plans after this foundation is working.

## File Structure

Create these files:

- `requirements-valuation.txt`: dependencies for the new valuation dashboard.
- `valuation_app/__init__.py`: package marker and version.
- `valuation_app/models.py`: Pydantic data models for observations, audit checks, input sets, and overrides.
- `valuation_app/calculations.py`: pure financial formulas with no I/O.
- `valuation_app/repository.py`: local JSON loading helpers.
- `valuation_app/audit.py`: converts observations into shared valuation inputs and audit checks.
- `valuation_app/formatting.py`: display helpers for Korean won and status labels.
- `valuation_app/dashboard.py`: Streamlit dashboard for Phase 1.
- `data/valuation/009150/normalized/metrics.json`: seed observations for Samsung Electro-Mechanics.
- `data/valuation/009150/normalized/market.json`: seed market data.
- `tests/test_valuation_models.py`: model validation tests.
- `tests/test_valuation_calculations.py`: formula tests.
- `tests/test_valuation_repository.py`: data loading tests.
- `tests/test_valuation_audit.py`: audit engine tests.
- `tests/test_valuation_formatting.py`: display helper tests.

Modify these files:

- `README.md`: add a short section explaining how to run the valuation dashboard.

---

### Task 1: Add Valuation Dashboard Dependencies and Package Shell

**Files:**
- Create: `requirements-valuation.txt`
- Create: `valuation_app/__init__.py`

- [ ] **Step 1: Verify the package does not import yet**

Run:

```powershell
python -c "import valuation_app"
```

Expected: FAIL with `ModuleNotFoundError: No module named 'valuation_app'`.

- [ ] **Step 2: Create `requirements-valuation.txt`**

Add this exact file:

```text
pydantic>=2.7.0
pytest>=8.2.0
streamlit>=1.35.0
```

- [ ] **Step 3: Create `valuation_app/__init__.py`**

Add this exact file:

```python
"""Samsung Electro-Mechanics implied valuation dashboard."""

__version__ = "0.1.0"
```

- [ ] **Step 4: Verify the package imports**

Run:

```powershell
python -c "import valuation_app; print(valuation_app.__version__)"
```

Expected: PASS and prints `0.1.0`.

- [ ] **Step 5: Commit**

```powershell
git add requirements-valuation.txt valuation_app/__init__.py
git commit -m "feat: add valuation app package shell"
```

---

### Task 2: Add Core Data Models

**Files:**
- Create: `tests/test_valuation_models.py`
- Create: `valuation_app/models.py`

- [ ] **Step 1: Write the failing model tests**

Create `tests/test_valuation_models.py`:

```python
import pytest
from pydantic import ValidationError

from valuation_app.models import AuditCheck, MetricObservation, UserOverride, ValuationInputSet


def test_metric_observation_keeps_source_lineage():
    obs = MetricObservation(
        metric_key="operating_income",
        label="영업이익",
        value=913_331_178_230,
        unit="KRW",
        period="2025A",
        source_method="dart_direct",
        report_year="2025",
        report_code="11011",
        statement_name="손익계산서",
        original_account_name="영업이익",
        original_amount=913_331_178_230,
        confidence=1.0,
        note="사업보고서 연결 기준",
    )

    assert obs.metric_key == "operating_income"
    assert obs.source_method == "dart_direct"
    assert obs.original_account_name == "영업이익"


def test_metric_observation_rejects_unknown_source_method():
    with pytest.raises(ValidationError):
        MetricObservation(
            metric_key="fcf",
            label="FCF",
            value=1,
            unit="KRW",
            period="2025A",
            source_method="spreadsheet_guess",
            confidence=0.5,
        )


def test_audit_check_records_formula_and_status():
    check = AuditCheck(
        check_key="fcf_reconciliation",
        label="FCF 검산",
        formula="FCF = 영업활동현금흐름 - CAPEX",
        expected_value=243_767_338_650,
        actual_value=243_767_338_650,
        tolerance=1,
        status="pass",
        inputs=["op_cashflow", "capex", "fcf"],
        explanation="보고된 FCF와 계산값이 일치합니다.",
    )

    assert check.status == "pass"
    assert "op_cashflow" in check.inputs


def test_input_set_and_override_models():
    input_set = ValuationInputSet(
        ticker="009150",
        company_name="삼성전기",
        valuation_date="2026-05-24",
        inputs={"market_cap": 101_233_310_302_208.0},
        observation_keys={"market_cap": "market_cap_2026_05_22"},
    )
    override = UserOverride(
        metric_key="tax_rate",
        previous_value=0.183,
        new_value=0.22,
        reason="장기 정상세율 민감도 확인",
        changed_at="2026-05-24T17:30:00+09:00",
    )

    assert input_set.inputs["market_cap"] == 101_233_310_302_208.0
    assert override.metric_key == "tax_rate"
```

- [ ] **Step 2: Run the model tests and verify failure**

Run:

```powershell
python -m pytest tests/test_valuation_models.py -v
```

Expected: FAIL with `ModuleNotFoundError` or import errors for missing models.

- [ ] **Step 3: Implement `valuation_app/models.py`**

Create `valuation_app/models.py`:

```python
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
```

- [ ] **Step 4: Run the model tests and verify pass**

Run:

```powershell
python -m pytest tests/test_valuation_models.py -v
```

Expected: PASS, four tests pass.

- [ ] **Step 5: Commit**

```powershell
git add valuation_app/models.py tests/test_valuation_models.py
git commit -m "feat: add valuation data models"
```

---

### Task 3: Add Pure Valuation Calculations

**Files:**
- Create: `tests/test_valuation_calculations.py`
- Create: `valuation_app/calculations.py`

- [ ] **Step 1: Write the failing formula tests**

Create `tests/test_valuation_calculations.py`:

```python
import pytest

from valuation_app.calculations import (
    calc_enterprise_value,
    calc_fcf,
    calc_invested_capital,
    calc_net_debt,
    calc_nopat,
    calc_required_fcf,
    calc_roic,
)


def test_calc_fcf_uses_positive_capex_outflow():
    assert calc_fcf(1_490_090_883_050, 1_246_323_544_400) == 243_767_338_650


def test_calc_net_debt_can_be_negative_for_net_cash_company():
    assert calc_net_debt(0, 2_277_190_926_336, 2_701_205_962_752) == -424_015_036_416


def test_calc_enterprise_value_from_market_cap_and_net_debt():
    ev = calc_enterprise_value(
        market_cap=101_233_310_302_208,
        net_debt=-424_015_036_416,
    )
    assert ev == 100_809_295_265_792


def test_calc_nopat_and_invested_capital_and_roic():
    nopat = calc_nopat(913_331_178_230, 0.183)
    invested_capital = calc_invested_capital(9_541_761_553_950, -424_015_036_416)
    roic = calc_roic(nopat, invested_capital)

    assert round(nopat) == 746_191_572_614
    assert invested_capital == 9_117_746_517_534
    assert round(roic, 4) == 0.0818


def test_calc_roic_returns_none_when_invested_capital_is_zero():
    assert calc_roic(100, 0) is None


def test_calc_required_fcf():
    assert calc_required_fcf(100_809_295_265_792, 0.09, 0.03) == pytest.approx(
        6_048_557_715_947.52
    )


def test_calc_required_fcf_rejects_invalid_terminal_spread():
    with pytest.raises(ValueError, match="WACC must be greater"):
        calc_required_fcf(100, 0.03, 0.03)
```

- [ ] **Step 2: Run the formula tests and verify failure**

Run:

```powershell
python -m pytest tests/test_valuation_calculations.py -v
```

Expected: FAIL with `ModuleNotFoundError` for `valuation_app.calculations`.

- [ ] **Step 3: Implement `valuation_app/calculations.py`**

Create `valuation_app/calculations.py`:

```python
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
```

- [ ] **Step 4: Run the formula tests and verify pass**

Run:

```powershell
python -m pytest tests/test_valuation_calculations.py -v
```

Expected: PASS, seven tests pass.

- [ ] **Step 5: Commit**

```powershell
git add valuation_app/calculations.py tests/test_valuation_calculations.py
git commit -m "feat: add valuation formulas"
```

---

### Task 4: Add Samsung Electro-Mechanics Seed Data and Repository Loader

**Files:**
- Create: `data/valuation/009150/normalized/metrics.json`
- Create: `data/valuation/009150/normalized/market.json`
- Create: `tests/test_valuation_repository.py`
- Create: `valuation_app/repository.py`

- [ ] **Step 1: Create seed data files**

Create `data/valuation/009150/normalized/metrics.json`:

```json
[
  {
    "metric_key": "revenue",
    "label": "매출액",
    "value": 11314459238100,
    "unit": "KRW",
    "period": "2025A",
    "source_method": "dart_direct",
    "report_year": "2025",
    "report_code": "11011",
    "statement_name": "손익계산서",
    "original_account_name": "매출액",
    "original_amount": 11314459238100,
    "confidence": 1.0,
    "note": "2025년 연간 연결 기준 seed data"
  },
  {
    "metric_key": "operating_income",
    "label": "영업이익",
    "value": 913331178230,
    "unit": "KRW",
    "period": "2025A",
    "source_method": "dart_direct",
    "report_year": "2025",
    "report_code": "11011",
    "statement_name": "손익계산서",
    "original_account_name": "영업이익",
    "original_amount": 913331178230,
    "confidence": 1.0,
    "note": "2025년 연간 연결 기준 seed data"
  },
  {
    "metric_key": "ebit",
    "label": "EBIT",
    "value": 972249110800,
    "unit": "KRW",
    "period": "2025A",
    "source_method": "dart_direct",
    "report_year": "2025",
    "report_code": "11011",
    "statement_name": "손익계산서",
    "original_account_name": "EBIT",
    "original_amount": 972249110800,
    "confidence": 0.9,
    "note": "영업외 항목 포함 여부는 Source Integrity 화면에서 표시"
  },
  {
    "metric_key": "tax_rate",
    "label": "유효세율",
    "value": 0.183,
    "unit": "ratio",
    "period": "2025A",
    "source_method": "calculated",
    "report_year": "2025",
    "report_code": "11011",
    "statement_name": "손익계산서",
    "original_account_name": "법인세비용 / 법인세차감전순이익",
    "original_amount": null,
    "confidence": 0.9,
    "note": "163,599,365,420 / 895,831,372,800 rounded"
  },
  {
    "metric_key": "op_cashflow",
    "label": "영업활동현금흐름",
    "value": 1490090883050,
    "unit": "KRW",
    "period": "2025A",
    "source_method": "dart_direct",
    "report_year": "2025",
    "report_code": "11011",
    "statement_name": "현금흐름표",
    "original_account_name": "영업활동으로 인한 현금흐름",
    "original_amount": 1490090883050,
    "confidence": 1.0,
    "note": "2025년 연간 연결 기준 seed data"
  },
  {
    "metric_key": "capex",
    "label": "CAPEX",
    "value": 1246323544400,
    "unit": "KRW",
    "period": "2025A",
    "source_method": "llm",
    "report_year": "2025",
    "report_code": "11011",
    "statement_name": "현금흐름표",
    "original_account_name": "유형자산의 취득",
    "original_amount": -1246323544400,
    "confidence": 0.85,
    "note": "원문은 현금유출 음수, 분석 입력은 양수 outflow로 정규화"
  },
  {
    "metric_key": "fcf",
    "label": "FCF",
    "value": 243767338650,
    "unit": "KRW",
    "period": "2025A",
    "source_method": "calculated",
    "report_year": "2025",
    "report_code": "11011",
    "statement_name": "현금흐름표",
    "original_account_name": "영업활동현금흐름 - CAPEX",
    "original_amount": null,
    "confidence": 1.0,
    "note": "1,490,090,883,050 - 1,246,323,544,400"
  },
  {
    "metric_key": "total_equity",
    "label": "자본총계",
    "value": 9541761553950,
    "unit": "KRW",
    "period": "2025A",
    "source_method": "dart_direct",
    "report_year": "2025",
    "report_code": "11011",
    "statement_name": "재무상태표",
    "original_account_name": "자본총계",
    "original_amount": 9541761553950,
    "confidence": 1.0,
    "note": "2025년 말 연결 기준 seed data"
  },
  {
    "metric_key": "cash",
    "label": "현금및현금성자산",
    "value": 2701205962752,
    "unit": "KRW",
    "period": "2025A",
    "source_method": "market",
    "report_year": "2025",
    "report_code": "11011",
    "statement_name": "재무상태표",
    "original_account_name": "cash and marketable securities",
    "original_amount": 2701205962752,
    "confidence": 0.8,
    "note": "시장 데이터 seed; DART 원문 연결 시 재검증"
  },
  {
    "metric_key": "short_debt",
    "label": "단기차입금",
    "value": 0,
    "unit": "KRW",
    "period": "2025A",
    "source_method": "market",
    "report_year": "2025",
    "report_code": "11011",
    "statement_name": "재무상태표",
    "original_account_name": "short debt split unavailable",
    "original_amount": 0,
    "confidence": 0.4,
    "note": "seed data에서 총부채 split이 없어 장기부채 쪽에 합산"
  },
  {
    "metric_key": "long_debt",
    "label": "장기차입금",
    "value": 2277190926336,
    "unit": "KRW",
    "period": "2025A",
    "source_method": "market",
    "report_year": "2025",
    "report_code": "11011",
    "statement_name": "재무상태표",
    "original_account_name": "total debt",
    "original_amount": 2277190926336,
    "confidence": 0.7,
    "note": "seed data에서 총차입금 전체를 long_debt로 둠"
  },
  {
    "metric_key": "net_debt",
    "label": "순부채",
    "value": -424015036416,
    "unit": "KRW",
    "period": "2025A",
    "source_method": "calculated",
    "report_year": "2025",
    "report_code": "11011",
    "statement_name": "재무상태표",
    "original_account_name": "총차입금 - 현금",
    "original_amount": null,
    "confidence": 0.8,
    "note": "2,277,190,926,336 - 2,701,205,962,752"
  },
  {
    "metric_key": "latest_quarter_revenue",
    "label": "최근 분기 매출액",
    "value": 3209100000000,
    "unit": "KRW",
    "period": "2026Q1",
    "source_method": "dart_direct",
    "report_year": "2026",
    "report_code": "11013",
    "statement_name": "손익계산서",
    "original_account_name": "매출액",
    "original_amount": 3209100000000,
    "confidence": 0.9,
    "note": "2026년 1분기 발표자료 seed data"
  },
  {
    "metric_key": "latest_quarter_operating_income",
    "label": "최근 분기 영업이익",
    "value": 280600000000,
    "unit": "KRW",
    "period": "2026Q1",
    "source_method": "dart_direct",
    "report_year": "2026",
    "report_code": "11013",
    "statement_name": "손익계산서",
    "original_account_name": "영업이익",
    "original_amount": 280600000000,
    "confidence": 0.9,
    "note": "2026년 1분기 발표자료 seed data"
  }
]
```

Create `data/valuation/009150/normalized/market.json`:

```json
{
  "ticker": "009150",
  "company_name": "삼성전기",
  "valuation_date": "2026-05-24",
  "market_data_as_of": "2026-05-22",
  "price": 1340000,
  "shares_outstanding": 72693696,
  "market_cap": 101233310302208,
  "reported_enterprise_value": 101064883830784,
  "currency": "KRW",
  "note": "seed data; 주말에는 마지막 거래일 기준으로 표시"
}
```

- [ ] **Step 2: Write the failing repository tests**

Create `tests/test_valuation_repository.py`:

```python
from pathlib import Path

from valuation_app.repository import load_market_data, load_metric_observations


ROOT = Path(__file__).resolve().parents[1]


def test_load_metric_observations_from_seed_data():
    observations = load_metric_observations(ROOT / "data/valuation/009150/normalized/metrics.json")
    keys = {obs.metric_key for obs in observations}

    assert "revenue" in keys
    assert "op_cashflow" in keys
    assert "latest_quarter_operating_income" in keys
    assert len(observations) >= 10


def test_load_market_data_from_seed_data():
    market = load_market_data(ROOT / "data/valuation/009150/normalized/market.json")

    assert market["ticker"] == "009150"
    assert market["market_cap"] == 101_233_310_302_208
    assert market["market_data_as_of"] == "2026-05-22"
```

- [ ] **Step 3: Run the repository tests and verify failure**

Run:

```powershell
python -m pytest tests/test_valuation_repository.py -v
```

Expected: FAIL with missing `valuation_app.repository`.

- [ ] **Step 4: Implement `valuation_app/repository.py`**

Create `valuation_app/repository.py`:

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from valuation_app.models import MetricObservation


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_metric_observations(path: Path) -> list[MetricObservation]:
    rows = load_json(path)
    return [MetricObservation.model_validate(row) for row in rows]


def load_market_data(path: Path) -> dict[str, Any]:
    data = load_json(path)
    required = {"ticker", "company_name", "valuation_date", "market_cap", "price"}
    missing = sorted(required - set(data.keys()))
    if missing:
        raise ValueError(f"Missing market data fields: {', '.join(missing)}")
    return data
```

- [ ] **Step 5: Run the repository tests and verify pass**

Run:

```powershell
python -m pytest tests/test_valuation_repository.py -v
```

Expected: PASS, two tests pass.

- [ ] **Step 6: Commit**

```powershell
git add data/valuation/009150/normalized/metrics.json data/valuation/009150/normalized/market.json valuation_app/repository.py tests/test_valuation_repository.py
git commit -m "feat: add Samsung Electro-Mechanics seed data"
```

---

### Task 5: Add Audit Engine

**Files:**
- Create: `tests/test_valuation_audit.py`
- Create: `valuation_app/audit.py`

- [ ] **Step 1: Write the failing audit tests**

Create `tests/test_valuation_audit.py`:

```python
from pathlib import Path

from valuation_app.audit import build_input_set, run_audit
from valuation_app.repository import load_market_data, load_metric_observations


ROOT = Path(__file__).resolve().parents[1]


def _load_seed():
    observations = load_metric_observations(ROOT / "data/valuation/009150/normalized/metrics.json")
    market = load_market_data(ROOT / "data/valuation/009150/normalized/market.json")
    return observations, market


def test_build_input_set_includes_market_and_financial_inputs():
    observations, market = _load_seed()
    input_set = build_input_set(observations, market)

    assert input_set.ticker == "009150"
    assert input_set.inputs["market_cap"] == 101_233_310_302_208
    assert input_set.inputs["fcf"] == 243_767_338_650
    assert input_set.inputs["latest_quarter_revenue"] == 3_209_100_000_000


def test_run_audit_calculates_passes_and_warning_for_reported_ev_gap():
    observations, market = _load_seed()
    input_set, checks, derived = run_audit(observations, market)
    statuses = {check.check_key: check.status for check in checks}
    derived_map = {obs.metric_key: obs.value for obs in derived}

    assert statuses["fcf_reconciliation"] == "pass"
    assert statuses["net_debt_reconciliation"] == "pass"
    assert statuses["reported_ev_gap"] == "warning"
    assert derived_map["enterprise_value"] == 100_809_295_265_792
    assert round(derived_map["roic"], 4) == 0.0818
    assert input_set.inputs["enterprise_value"] == 100_809_295_265_792
```

- [ ] **Step 2: Run the audit tests and verify failure**

Run:

```powershell
python -m pytest tests/test_valuation_audit.py -v
```

Expected: FAIL with missing `valuation_app.audit`.

- [ ] **Step 3: Implement `valuation_app/audit.py`**

Create `valuation_app/audit.py`:

```python
from __future__ import annotations

from valuation_app.calculations import (
    calc_enterprise_value,
    calc_fcf,
    calc_invested_capital,
    calc_net_debt,
    calc_nopat,
    calc_roic,
)
from valuation_app.models import AuditCheck, MetricObservation, ValuationInputSet


def _observation_map(observations: list[MetricObservation]) -> dict[str, MetricObservation]:
    return {obs.metric_key: obs for obs in observations}


def _value(metrics: dict[str, MetricObservation], key: str) -> float | None:
    obs = metrics.get(key)
    return None if obs is None else obs.value


def _status(expected: float | None, actual: float | None, tolerance: float) -> str:
    if expected is None or actual is None:
        return "fail"
    return "pass" if abs(expected - actual) <= tolerance else "warning"


def _calculated_observation(metric_key: str, label: str, value: float | None, period: str, note: str) -> MetricObservation:
    return MetricObservation(
        metric_key=metric_key,
        label=label,
        value=value,
        unit="ratio" if metric_key == "roic" else "KRW",
        period=period,
        source_method="calculated",
        confidence=1.0 if value is not None else 0.0,
        note=note,
    )


def build_input_set(observations: list[MetricObservation], market: dict) -> ValuationInputSet:
    metrics = _observation_map(observations)
    inputs = {key: obs.value for key, obs in metrics.items()}
    inputs["price"] = float(market["price"])
    inputs["shares_outstanding"] = float(market["shares_outstanding"])
    inputs["market_cap"] = float(market["market_cap"])
    observation_keys = {key: key for key in inputs.keys()}

    return ValuationInputSet(
        ticker=market["ticker"],
        company_name=market["company_name"],
        valuation_date=market["valuation_date"],
        inputs=inputs,
        observation_keys=observation_keys,
    )


def run_audit(
    observations: list[MetricObservation],
    market: dict,
) -> tuple[ValuationInputSet, list[AuditCheck], list[MetricObservation]]:
    metrics = _observation_map(observations)
    checks: list[AuditCheck] = []
    derived: list[MetricObservation] = []

    op_cashflow = _value(metrics, "op_cashflow")
    capex = _value(metrics, "capex")
    reported_fcf = _value(metrics, "fcf")
    calculated_fcf = None if op_cashflow is None or capex is None else calc_fcf(op_cashflow, capex)
    checks.append(
        AuditCheck(
            check_key="fcf_reconciliation",
            label="FCF 검산",
            formula="FCF = 영업활동현금흐름 - CAPEX",
            expected_value=calculated_fcf,
            actual_value=reported_fcf,
            tolerance=1.0,
            status=_status(calculated_fcf, reported_fcf, 1.0),
            inputs=["op_cashflow", "capex", "fcf"],
            explanation="CAPEX는 양수 현금유출로 정규화한 뒤 영업현금흐름에서 차감합니다.",
        )
    )

    short_debt = _value(metrics, "short_debt")
    long_debt = _value(metrics, "long_debt")
    cash = _value(metrics, "cash")
    reported_net_debt = _value(metrics, "net_debt")
    calculated_net_debt = (
        None if short_debt is None or long_debt is None or cash is None else calc_net_debt(short_debt, long_debt, cash)
    )
    checks.append(
        AuditCheck(
            check_key="net_debt_reconciliation",
            label="순부채 검산",
            formula="순부채 = 단기차입금 + 장기차입금 - 현금",
            expected_value=calculated_net_debt,
            actual_value=reported_net_debt,
            tolerance=1.0,
            status=_status(calculated_net_debt, reported_net_debt, 1.0),
            inputs=["short_debt", "long_debt", "cash", "net_debt"],
            explanation="순현금 기업이면 순부채는 음수가 됩니다.",
        )
    )

    enterprise_value = None
    if calculated_net_debt is not None:
        enterprise_value = calc_enterprise_value(float(market["market_cap"]), calculated_net_debt)
        derived.append(
            _calculated_observation(
                "enterprise_value",
                "EV",
                enterprise_value,
                market["valuation_date"],
                "EV = 시가총액 + 순부채",
            )
        )

    reported_ev = market.get("reported_enterprise_value")
    ev_status = "fail"
    ev_explanation = "EV 계산값을 만들 수 없습니다."
    if enterprise_value is not None and reported_ev is not None:
        gap = abs(enterprise_value - float(reported_ev))
        ev_status = "pass" if gap <= 100_000_000_000 else "warning"
        ev_explanation = "시장 데이터 제공자의 EV와 직접 계산한 EV가 다르면 구성 항목 차이를 확인합니다."
    checks.append(
        AuditCheck(
            check_key="reported_ev_gap",
            label="EV 제공값 비교",
            formula="EV = 시가총액 + 순부채",
            expected_value=enterprise_value,
            actual_value=float(reported_ev) if reported_ev is not None else None,
            tolerance=100_000_000_000.0,
            status=ev_status,
            inputs=["market_cap", "net_debt", "reported_enterprise_value"],
            explanation=ev_explanation,
        )
    )

    operating_income = _value(metrics, "operating_income")
    tax_rate = _value(metrics, "tax_rate")
    nopat = None if operating_income is None or tax_rate is None else calc_nopat(operating_income, tax_rate)
    derived.append(_calculated_observation("nopat", "NOPAT", nopat, "2025A", "NOPAT = 영업이익 × (1 - 세율)"))

    total_equity = _value(metrics, "total_equity")
    invested_capital = None if total_equity is None or calculated_net_debt is None else calc_invested_capital(total_equity, calculated_net_debt)
    derived.append(
        _calculated_observation(
            "invested_capital",
            "투하자본",
            invested_capital,
            "2025A",
            "투하자본 = 자본총계 + 순부채",
        )
    )

    roic = None if nopat is None or invested_capital is None else calc_roic(nopat, invested_capital)
    derived.append(_calculated_observation("roic", "ROIC", roic, "2025A", "ROIC = NOPAT / 투하자본"))

    input_set = build_input_set(observations + derived, market)
    return input_set, checks, derived
```

- [ ] **Step 4: Run the audit tests and verify pass**

Run:

```powershell
python -m pytest tests/test_valuation_audit.py -v
```

Expected: PASS, two tests pass.

- [ ] **Step 5: Commit**

```powershell
git add valuation_app/audit.py tests/test_valuation_audit.py
git commit -m "feat: add valuation data audit engine"
```

---

### Task 6: Add Display Formatting Helpers

**Files:**
- Create: `tests/test_valuation_formatting.py`
- Create: `valuation_app/formatting.py`

- [ ] **Step 1: Write the failing formatting tests**

Create `tests/test_valuation_formatting.py`:

```python
from valuation_app.formatting import format_krw, format_ratio, status_label, source_label


def test_format_krw_uses_trillion_and_billion_units():
    assert format_krw(101_233_310_302_208) == "101.2조원"
    assert format_krw(913_331_178_230) == "9,133억원"
    assert format_krw(-424_015_036_416) == "-4,240억원"


def test_format_ratio():
    assert format_ratio(0.0819) == "8.2%"
    assert format_ratio(None) == "-"


def test_status_label():
    assert status_label("pass") == "통과"
    assert status_label("warning") == "확인 필요"
    assert status_label("fail") == "실패"


def test_source_label():
    assert source_label("dart_direct") == "DART"
    assert source_label("calculated") == "CALC"
    assert source_label("market") == "MARKET"
    assert source_label("manual") == "MANUAL"
```

- [ ] **Step 2: Run the formatting tests and verify failure**

Run:

```powershell
python -m pytest tests/test_valuation_formatting.py -v
```

Expected: FAIL with missing `valuation_app.formatting`.

- [ ] **Step 3: Implement `valuation_app/formatting.py`**

Create `valuation_app/formatting.py`:

```python
from __future__ import annotations


def format_krw(value: float | None) -> str:
    if value is None:
        return "-"
    sign = "-" if value < 0 else ""
    abs_value = abs(value)
    if abs_value >= 1_000_000_000_000:
        return f"{sign}{abs_value / 1_000_000_000_000:.1f}조원"
    return f"{sign}{abs_value / 100_000_000:,.0f}억원"


def format_ratio(value: float | None) -> str:
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
```

- [ ] **Step 4: Run the formatting tests and verify pass**

Run:

```powershell
python -m pytest tests/test_valuation_formatting.py -v
```

Expected: PASS, four tests pass.

- [ ] **Step 5: Commit**

```powershell
git add valuation_app/formatting.py tests/test_valuation_formatting.py
git commit -m "feat: add valuation display formatting"
```

---

### Task 7: Add Phase 1 Streamlit Dashboard

**Files:**
- Create: `valuation_app/dashboard.py`

- [ ] **Step 1: Verify dashboard entrypoint fails before creation**

Run:

```powershell
python -m streamlit run valuation_app/dashboard.py --server.headless true
```

Expected: FAIL because `valuation_app/dashboard.py` does not exist.

- [ ] **Step 2: Implement `valuation_app/dashboard.py`**

Create `valuation_app/dashboard.py`:

```python
from __future__ import annotations

from pathlib import Path

import streamlit as st

from valuation_app.audit import run_audit
from valuation_app.formatting import format_krw, format_ratio, source_label, status_label
from valuation_app.models import AuditCheck, MetricObservation
from valuation_app.repository import load_market_data, load_metric_observations


ROOT = Path(__file__).resolve().parents[1]
METRICS_PATH = ROOT / "data/valuation/009150/normalized/metrics.json"
MARKET_PATH = ROOT / "data/valuation/009150/normalized/market.json"


def _metric_map(observations: list[MetricObservation]) -> dict[str, MetricObservation]:
    return {obs.metric_key: obs for obs in observations}


def _display_value(obs: MetricObservation) -> str:
    if obs.unit == "ratio":
        return format_ratio(obs.value)
    return format_krw(obs.value)


def _check_rows(checks: list[AuditCheck]) -> list[dict[str, str]]:
    rows = []
    for check in checks:
        rows.append(
            {
                "검산": check.label,
                "상태": status_label(check.status),
                "공식": check.formula,
                "계산값": format_krw(check.expected_value),
                "비교값": format_krw(check.actual_value),
                "설명": check.explanation,
            }
        )
    return rows


def _observation_rows(observations: list[MetricObservation]) -> list[dict[str, str]]:
    rows = []
    for obs in observations:
        rows.append(
            {
                "입력값": obs.label,
                "값": _display_value(obs),
                "기간": obs.period,
                "출처": source_label(obs.source_method),
                "보고서": obs.report_code or "-",
                "원문 계정": obs.original_account_name or "-",
                "신뢰도": format_ratio(obs.confidence),
                "메모": obs.note,
            }
        )
    return rows


def render_source_panel(obs: MetricObservation) -> None:
    st.markdown(f"#### {obs.label}")
    st.write(f"값: **{_display_value(obs)}**")
    st.write(f"출처: **{source_label(obs.source_method)}**")
    st.write(f"기간: `{obs.period}`")
    st.write(f"보고서 코드: `{obs.report_code or '-'}`")
    st.write(f"재무제표: `{obs.statement_name or '-'}`")
    st.write(f"원문 계정명: `{obs.original_account_name or '-'}`")
    st.write(f"원문 금액: `{format_krw(obs.original_amount) if obs.original_amount is not None else '-'}`")
    st.write(f"신뢰도: `{format_ratio(obs.confidence)}`")
    st.info(obs.note or "메모 없음")


def main() -> None:
    st.set_page_config(page_title="삼성전기 가치분석", layout="wide")
    st.title("삼성전기 시장내포 가치분석")
    st.caption("Phase 1: 결론 전에 출처, 공식, 검산부터 확인합니다.")

    observations = load_metric_observations(METRICS_PATH)
    market = load_market_data(MARKET_PATH)
    input_set, checks, derived = run_audit(observations, market)
    all_observations = observations + derived
    metrics = _metric_map(all_observations)

    st.subheader("시장 기준")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("현재가", format_krw(market["price"]))
    c2.metric("시가총액", format_krw(market["market_cap"]))
    c3.metric("직접 계산 EV", format_krw(input_set.inputs.get("enterprise_value")))
    c4.metric("시장 데이터 기준일", market["market_data_as_of"])

    st.subheader("핵심 입력값")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("2025 매출", format_krw(input_set.inputs.get("revenue")))
    k2.metric("2025 영업이익", format_krw(input_set.inputs.get("operating_income")))
    k3.metric("2025 FCF", format_krw(input_set.inputs.get("fcf")))
    k4.metric("계산 ROIC", format_ratio(input_set.inputs.get("roic")))

    q1, q2 = st.columns(2)
    q1.metric("2026 Q1 매출", format_krw(input_set.inputs.get("latest_quarter_revenue")))
    q2.metric("2026 Q1 영업이익", format_krw(input_set.inputs.get("latest_quarter_operating_income")))

    tab_audit, tab_inputs, tab_formula, tab_source = st.tabs(
        ["1. 검산", "2. 입력값", "3. 공식", "4. 출처 상세"]
    )

    with tab_audit:
        st.markdown("검산이 통과하지 않은 값은 다음 가치평가 렌즈로 넘기기 전에 확인합니다.")
        st.dataframe(_check_rows(checks), use_container_width=True, hide_index=True)

    with tab_inputs:
        st.markdown("같은 입력값을 Reverse DCF, Value Attribution, ROIC, 상대가치 렌즈가 공유합니다.")
        st.dataframe(_observation_rows(all_observations), use_container_width=True, hide_index=True)

    with tab_formula:
        st.markdown(
            """
            - `FCF = 영업활동현금흐름 - CAPEX`
            - `순부채 = 단기차입금 + 장기차입금 - 현금`
            - `EV = 시가총액 + 순부채`
            - `NOPAT = 영업이익 × (1 - 세율)`
            - `투하자본 = 자본총계 + 순부채`
            - `ROIC = NOPAT / 투하자본`
            """
        )
        st.warning("이 화면은 투자 권유가 아니라 다음 가치평가 단계로 넘길 입력값의 신뢰도를 확인하는 화면입니다.")

    with tab_source:
        selected_label = st.selectbox(
            "출처를 볼 입력값",
            options=[obs.label for obs in all_observations],
        )
        selected = next(obs for obs in all_observations if obs.label == selected_label)
        render_source_panel(selected)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run all tests**

Run:

```powershell
python -m pytest tests/test_valuation_models.py tests/test_valuation_calculations.py tests/test_valuation_repository.py tests/test_valuation_audit.py tests/test_valuation_formatting.py -v
```

Expected: PASS, all tests pass.

- [ ] **Step 4: Launch the dashboard**

Run:

```powershell
python -m streamlit run valuation_app/dashboard.py --server.port 8501
```

Expected: Streamlit prints a local URL. Open the URL and verify the page shows:

- market 기준 cards
- 2025 annual metrics
- 2026 Q1 metrics
- 검산 tab
- 입력값 tab
- 공식 tab
- 출처 상세 tab

- [ ] **Step 5: Commit**

```powershell
git add valuation_app/dashboard.py
git commit -m "feat: add Samsung Electro-Mechanics data integrity dashboard"
```

---

### Task 8: Add README Run Instructions

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add this section near the quick start section**

Append this exact Markdown block to `README.md`:

```markdown

---

## 삼성전기 가치분석 대시보드

삼성전기 `009150`을 한 종목씩 깊게 분석하기 위한 시장내포 가치분석 도구입니다. 첫 화면은 가치평가 결론이 아니라 데이터 무결성 확인입니다.

### 설치

```bash
pip install -r requirements-valuation.txt
```

### 테스트

```bash
python -m pytest tests/test_valuation_models.py tests/test_valuation_calculations.py tests/test_valuation_repository.py tests/test_valuation_audit.py tests/test_valuation_formatting.py -v
```

### 실행

```bash
python -m streamlit run valuation_app/dashboard.py --server.port 8501
```

### 현재 구현 범위

- 2025년 연간 seed data
- 2026년 1분기 seed data
- 주가, 주식수, 시가총액, EV 계산 입력
- FCF, 순부채, NOPAT, 투하자본, ROIC 검산
- 입력값별 출처 상세 패널

이 화면에서 검산을 통과한 공통 입력값을 다음 단계인 Reverse DCF와 Value Attribution 렌즈가 사용합니다.
```

- [ ] **Step 2: Run tests after README change**

Run:

```powershell
python -m pytest tests/test_valuation_models.py tests/test_valuation_calculations.py tests/test_valuation_repository.py tests/test_valuation_audit.py tests/test_valuation_formatting.py -v
```

Expected: PASS, all tests pass.

- [ ] **Step 3: Commit**

```powershell
git add README.md
git commit -m "docs: document valuation dashboard"
```

---

### Task 9: Final Verification for Phase 1

**Files:**
- No file changes.

- [ ] **Step 1: Check Git status**

Run:

```powershell
git status --short
```

Expected: no modified tracked files. Untracked `.superpowers/` can remain because it is the brainstorming browser companion output.

- [ ] **Step 2: Run the full Phase 1 test suite**

Run:

```powershell
python -m pytest tests/test_valuation_models.py tests/test_valuation_calculations.py tests/test_valuation_repository.py tests/test_valuation_audit.py tests/test_valuation_formatting.py -v
```

Expected: PASS, all tests pass.

- [ ] **Step 3: Launch the Streamlit app**

Run:

```powershell
python -m streamlit run valuation_app/dashboard.py --server.port 8501
```

Expected: browser can open `http://localhost:8501` and show the Samsung Electro-Mechanics data integrity dashboard.

- [ ] **Step 4: Manual screen checks**

Verify these items:

- The page does not start with a price target or investment conclusion.
- The first visible section shows market 기준 and source integrity.
- FCF formula is visible.
- Net debt formula is visible.
- EV formula is visible.
- Annual and latest-quarter data appear together.
- Source labels distinguish `DART`, `LLM`, `CALC`, and `MARKET`.
- The reported EV gap appears as `확인 필요`, not as a silent error.

---

## Self-Review Notes

Spec coverage:

- Phase 1 Source Integrity is covered by Tasks 2 through 7.
- Annual and latest-quarter seed data are covered by Task 4.
- Formula transparency is covered by Tasks 3, 5, 6, and 7.
- Manual override storage is modeled in Task 2 but not shown in the Phase 1 UI. That is acceptable for Phase 1 because the approved first implementation is data integrity display; editing controls belong in the next plan.
- Google Sheets and Damodaran export are not included because the spec marks them as optional export after the shared input layer exists.

Type consistency:

- `MetricObservation.metric_key` is used consistently across repository, audit, and dashboard.
- `AuditCheck.status` values match the status formatter.
- Monetary values use KRW numeric values, not 억원-scaled values, inside calculations.
