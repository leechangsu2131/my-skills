#!/usr/bin/env python3
"""Check all subjects and standards that need NEIS entry."""
import json
from pathlib import Path
from collections import defaultdict

data = json.loads(Path("scratch/neis-achievement-levels.json").read_text(encoding="utf-8"))

# Group by subject -> standard_code -> assessment
by_subject = defaultdict(lambda: defaultdict(dict))
for r in data:
    key = r["standard_code"] or r["assessment"]
    by_subject[r["subject"]][key]["assessment"] = r["assessment"]
    by_subject[r["subject"]][key]["count"] = by_subject[r["subject"]][key].get("count", 0) + 1
    by_subject[r["subject"]][key]["inferred"] = by_subject[r["subject"]][key].get("inferred", 0) + (1 if r["inferred"] else 0)

print("=" * 70)
print("전체 과목/영역/성취기준 목록")
print("=" * 70)

total_standards = 0
for subject, standards in sorted(by_subject.items()):
    print(f"\n## {subject}")
    for code, info in sorted(standards.items()):
        total_standards += 1
        inferred_tag = f" (추정 {info['inferred']}건)" if info["inferred"] > 0 else ""
        print(f"  [{code}] {info['assessment']} - {info['count']}명{inferred_tag}")

print(f"\n총 {total_standards}개 성취기준, {len(data)}건 레코드")
print(f"과목: {', '.join(sorted(by_subject.keys()))}")

# Known completed (from ing.md and current check)
print("\n" + "=" * 70)
print("진행 상황 (확인된 것)")
print("=" * 70)
print("✅ 국어 [4국01-01] 듣기·말하기 - 저장 완료 (ing.md 기록)")
print("✅ 국어 [4국05-04/05] 문학 - 저장 완료 (방금 확인)")
print("❌ 나머지 모든 과목/영역 - 미입력")
