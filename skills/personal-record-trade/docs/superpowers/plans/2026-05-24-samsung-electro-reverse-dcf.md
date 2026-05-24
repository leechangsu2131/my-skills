# Samsung Electro-Mechanics Reverse DCF Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Phase 2 to the Samsung Electro-Mechanics valuation tool: a Reverse DCF lens that shows the FCF level implied by the current EV under WACC and terminal-growth assumptions.

**Architecture:** Keep formulas in a small pure helper module and render the lens as a new Streamlit tab that consumes the audited Phase 1 input set. The screen should show the formula, source inputs, WACC/g sensitivity, and a simple normalized FCF thought experiment.

**Tech Stack:** Python 3, pytest, Streamlit.

---

### Task 1: Add Reverse DCF Helpers

**Files:**
- Create: `valuation_app/reverse_dcf.py`
- Create: `tests/test_reverse_dcf.py`

- [ ] Add tests for required FCF multiples, sensitivity rows, and normalized FCF.
- [ ] Implement helpers using existing `calc_required_fcf`.
- [ ] Run `python -m pytest tests/test_reverse_dcf.py -v`.

### Task 2: Add Reverse DCF Dashboard Tab

**Files:**
- Modify: `valuation_app/dashboard.py`

- [ ] Add a `Reverse DCF` tab after the input table.
- [ ] Show `필요 FCF1 = EV × (WACC - g)`.
- [ ] Use audited `enterprise_value`, `fcf`, `revenue`, `tax_rate`, and latest-quarter figures.
- [ ] Show WACC/g sliders, required FCF, current FCF multiple, sensitivity table, and normalized FCF scenario.
- [ ] Run the full valuation test suite and `python -m py_compile valuation_app/dashboard.py`.

### Task 3: Update README

**Files:**
- Modify: `README.md`

- [ ] Mention Reverse DCF in the dashboard scope.
- [ ] Run the full valuation test suite.

### Task 4: Final Verification

- [ ] Run all valuation tests.
- [ ] Verify Streamlit health at `http://localhost:8501/_stcore/health`.
- [ ] Commit the Phase 2 changes.
