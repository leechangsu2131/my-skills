"""분할기 결과(groups.json)에 연간지도계획의 차시·차시명·단원 이름을 입힌다.

분할기는 쪽 범위는 잘 찾지만 제목이 깨지거나 묶음 차시(5~6차시)를 1차시로 세는 경우가 있다.
연간지도계획의 차시 목록과 분할 묶음 수가 같으면 순서대로 짝지어 제목·차시를 고친다.

    python apply_annual_plan.py --groups "D:\\지도서\\사회 3-2\\[사회]3-2_지도서_1단원\\groups.json" \\
        --plan "D:\\지도서\\사회 3-2\\[사회]3-2_연간지도계획_1.pdf" --lessons 1-18 --unit "1. 사회 변화와 다양한 문화" [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

import fitz

ENTRY_RE = re.compile(
    r"(?<![\d.])(?P<a>\d{1,2})\s*(?:~\s*(?P<b>\d{1,2}))?\s+(?:(?P=a)\s*(?:~\s*(?P=b))?\s+)?"
    r"(?P<title>[^\d~]+?)\s+(?P<p1>\d{1,3})\s*~\s*(?P<p2>\d{1,3})(?!\d)")
EXTRA_CUT = re.compile(r"\s+(?:할 수 있어요|풍덩 사회 속으로|별별 직업 속으로|디지털 \+)")
CONTROL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\u200b-\u200d\ufeff]")


def plan_entries(pdf: Path) -> list[dict]:
    doc = fitz.open(pdf)
    text = " ".join(" ".join(CONTROL_RE.sub(" ", p.get_text()).split()) for p in doc)
    entries, seen = [], set()
    for m in ENTRY_RE.finditer(text):
        a = int(m["a"])
        b = int(m["b"]) if m["b"] else a
        title = EXTRA_CUT.split(m["title"].strip())[0].strip()
        if a in seen or b < a or not title or title.startswith(("연간", "차시", "단원 단원", "단원 주제")):
            continue
        seen.add(a)
        entries.append({"from": a, "to": b, "title": title, "textbook_pages": f"{m['p1']}~{m['p2']}"})
    return sorted(entries, key=lambda e: e["from"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--groups", required=True)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--lessons", required=True, help="이 분할 결과가 맡는 차시 범위, 예: 1-18")
    ap.add_argument("--unit", required=True, help="단원 이름, 예: '1. 사회 변화와 다양한 문화'")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    lo, hi = (int(x) for x in args.lessons.split("-"))
    entries = [e for e in plan_entries(Path(args.plan)) if lo <= e["from"] <= hi]
    path = Path(args.groups)
    data = json.loads(path.read_text(encoding="utf-8"))
    groups = [g for g in data.get("groups", []) if str(g.get("detected_level", "")).lower() not in {"section", "plan"}]
    print(f"연간지도계획 {len(entries)}개 · 분할 묶음 {len(groups)}개")
    if len(entries) != len(groups):
        for e in entries:
            print(f"   계획 {e['from']}~{e['to']} {e['title']}")
        for g in groups:
            print(f"   분할 p{g['start_page']}-{g['end_page']} {g.get('title', '')[:30]}")
        raise SystemExit("개수가 달라 자동으로 짝지을 수 없어요. 위 목록을 보고 분할을 고친 뒤 다시 실행하세요.")

    for g, e in zip(groups, entries):
        span = e["to"] - e["from"] + 1
        print(f"   {e['from']}{'~' + str(e['to']) if span > 1 else ''}차시 {e['title']}  ← p{g['start_page']}-{g['end_page']} ({g.get('title', '')[:20]})")
        g.update({"source_title": g.get("title", ""), "title": e["title"], "parent_unit_title": args.unit,
                  "lesson_span": span, "lesson_range": f"{e['from']}~{e['to']}" if span > 1 else str(e["from"]),
                  "textbook_pages": e["textbook_pages"]})
    if args.dry_run:
        print("[미리보기] --dry-run 을 빼면 groups.json 을 고칩니다(원본은 groups.orig.json 으로 보관).")
        return
    backup = path.with_name("groups.orig.json")
    if not backup.exists():
        shutil.copyfile(path, backup)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[저장] {path}")


if __name__ == "__main__":
    main()
