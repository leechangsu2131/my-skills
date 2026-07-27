#!/usr/bin/env python3
"""Filter Korean literature (문학) records for NEIS entry."""
import json
from pathlib import Path

data = json.loads(Path("scratch/neis-achievement-levels.json").read_text(encoding="utf-8"))

# 국어 문학영역: 4국05-04/05 (1단원: 시 낭송)
korean_lit = [r for r in data if r["subject"] == "국어" and r["standard_code"] == "4국05-04/05"]

print(f"records: {len(korean_lit)}")
for r in korean_lit:
    tag = " (추정)" if r["inferred"] else ""
    print(f"  {r['student']}: {r['level']}{tag}")

out = Path("scratch/neis-achievement-levels-korean-4guk0504.json")
out.write_text(json.dumps(korean_lit, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nSaved to {out}")
