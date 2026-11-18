#!/usr/bin/env python3
"""Filter Korean literature (문학) records for NEIS entry."""
import json
from pathlib import Path
import sys as _sys, pathlib as _pl; _sys.path.insert(0, str(next(p / "_shared" for p in _pl.Path(__file__).resolve().parents if (p / "_shared" / "skill_env.py").is_file())))
from skill_env import data_dir
NEIS_DATA = data_dir("admin-neis-bot")  # 내 문서\my-skills-data\admin-neis-bot (학생 데이터)


data = json.loads((NEIS_DATA / "neis-achievement-levels.json").read_text(encoding="utf-8"))

# 국어 문학영역: 4국05-04/05 (1단원: 시 낭송)
korean_lit = [r for r in data if r["subject"] == "국어" and r["standard_code"] == "4국05-04/05"]

print(f"records: {len(korean_lit)}")
for r in korean_lit:
    tag = " (추정)" if r["inferred"] else ""
    print(f"  {r['student']}: {r['level']}{tag}")

out = (NEIS_DATA / "neis-achievement-levels-korean-4guk0504.json")
out.write_text(json.dumps(korean_lit, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nSaved to {out}")
