import pytest

from valuation_app.models import ValuationInputSet
from valuation_app.synthesis import (
    build_next_quarter_checklist,
    build_synthesis_explanation,
    evaluate_signals,
)


def _build_dummy_input_set(ev: float | None, nopat: float | None, fcf: float | None, roic: float | None) -> ValuationInputSet:
    inputs = {}
    if ev is not None:
        inputs["enterprise_value"] = ev
    if nopat is not None:
        inputs["nopat"] = nopat
    if fcf is not None:
        inputs["fcf"] = fcf
    if roic is not None:
        inputs["roic"] = roic
    return ValuationInputSet(
        ticker="000000",
        company_name="Dummy",
        valuation_date="2026-05-25",
        observation_keys={},
        inputs=inputs
    )


def test_evaluate_signals_growth_ratio_high():
    # High growth expectation
    input_set = _build_dummy_input_set(ev=1000, nopat=10, fcf=10, roic=0.1)
    signals = evaluate_signals(input_set, wacc_assumption=0.10)
    
    growth_signal = next(s for s in signals if s["분야"] == "미래 성장 기대감")
    assert growth_signal["상태"] == "고성장 기대 (부담)"


def test_evaluate_signals_growth_ratio_low():
    # Low growth expectation
    input_set = _build_dummy_input_set(ev=100, nopat=15, fcf=10, roic=0.1)
    signals = evaluate_signals(input_set, wacc_assumption=0.10)
    
    growth_signal = next(s for s in signals if s["분야"] == "미래 성장 기대감")
    assert growth_signal["상태"] == "저성장 기대 (여유)"


def test_evaluate_signals_fcf_multiple_high():
    # EV is 1000, WACC is 0.1, g is 0.03 -> required FCF = 1000 * 0.07 = 70.
    # Current FCF = 1. Multiple = 70x.
    input_set = _build_dummy_input_set(ev=1000, nopat=10, fcf=1, roic=0.1)
    signals = evaluate_signals(input_set, wacc_assumption=0.10, terminal_growth=0.03)
    
    fcf_signal = next(s for s in signals if s["분야"] == "요구 현금흐름(FCF) 부담")
    assert fcf_signal["상태"] == "높은 턴어라운드 요구"


def test_evaluate_signals_roic_spread_negative():
    # WACC = 0.1, ROIC = 0.05 -> Spread = -0.05
    input_set = _build_dummy_input_set(ev=1000, nopat=10, fcf=10, roic=0.05)
    signals = evaluate_signals(input_set, wacc_assumption=0.10)
    
    roic_signal = next(s for s in signals if s["분야"] == "현재 자본 효율성(ROIC)")
    assert roic_signal["상태"] == "가치 파괴 구간"
    assert roic_signal["핵심 수치"] == pytest.approx(-0.05)


def test_evaluate_signals_ignores_missing_inputs():
    input_set = _build_dummy_input_set(ev=None, nopat=None, fcf=None, roic=None)
    signals = evaluate_signals(input_set)
    assert len(signals) == 0


def test_build_next_quarter_checklist_returns_items():
    checklist = build_next_quarter_checklist()
    assert len(checklist) > 0
    for item in checklist:
        assert "카테고리" in item
        assert "확인 포인트" in item
        assert "판단 기준" in item


def test_build_synthesis_explanation_is_not_empty():
    explanation = build_synthesis_explanation()
    assert len(explanation) > 0
    assert "마법 구슬" in explanation
