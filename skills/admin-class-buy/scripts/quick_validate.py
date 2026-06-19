#!/usr/bin/env python
"""Validate the admin-class-buy skill files without touching K-에듀파인."""

from __future__ import annotations

import py_compile
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require_file(path: Path) -> str:
    if not path.exists():
        raise AssertionError(f"missing file: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def main() -> int:
    skill = require_file(ROOT / "SKILL.md")
    rules = require_file(ROOT / "references" / "class_fund_rules.md")
    workflow = require_file(ROOT / "references" / "edufine_workflow.md")
    troubleshooting = require_file(ROOT / "문제해결.md")

    required_terms = {
        "SKILL.md": (skill, ["admin-class-buy", "개산급정산등록", "문제해결.md"]),
        "class_fund_rules.md": (rules, ["20,000", "증빙자료", "정산"]),
        "edufine_workflow.md": (workflow, ["Chrome remote debugging", "개산급정산등록", "2026-03-01"]),
        "문제해결.md": (troubleshooting, ["실제 실행", "해결"]),
    }
    for label, (text, terms) in required_terms.items():
        for term in terms:
            if term not in text:
                raise AssertionError(f"{label} does not contain required term: {term}")

    scripts = [
        ROOT / "scripts" / "generate_evidence_docx.py",
        ROOT / "scripts" / "edufine_class_settlement.py",
    ]
    for script in scripts:
        py_compile.compile(str(script), doraise=True)

    print("admin-class-buy quick validation passed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"validation failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
