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


def test_metric_observation_rejects_extra_fields():
    with pytest.raises(ValidationError):
        MetricObservation(
            metric_key="revenue",
            label="Revenue",
            value=1,
            period="2025A",
            source_method="manual",
            confidence=0.5,
            source_methd="manual",
        )


def test_valuation_input_set_rejects_invalid_valuation_date():
    with pytest.raises(ValidationError):
        ValuationInputSet(
            ticker="009150",
            company_name="Samsung Electro-Mechanics",
            valuation_date="2026-13-40",
            inputs={"market_cap": 1},
            observation_keys={"market_cap": "market_cap_2026_05_22"},
        )


def test_user_override_rejects_invalid_changed_at():
    with pytest.raises(ValidationError):
        UserOverride(
            metric_key="tax_rate",
            previous_value=0.183,
            new_value=0.22,
            reason="Sensitivity check",
            changed_at="not-a-datetime",
        )


def test_metric_observation_rejects_confidence_outside_bounds():
    with pytest.raises(ValidationError):
        MetricObservation(
            metric_key="fcf",
            label="FCF",
            value=1,
            period="2025A",
            source_method="manual",
            confidence=1.1,
        )


def test_audit_check_rejects_negative_tolerance():
    with pytest.raises(ValidationError):
        AuditCheck(
            check_key="fcf_reconciliation",
            label="FCF check",
            formula="FCF = CFO - CAPEX",
            expected_value=1,
            actual_value=1,
            tolerance=-0.01,
            status="pass",
            inputs=["op_cashflow", "capex"],
            explanation="No negative tolerances.",
        )
