#!/usr/bin/env python3
"""Parse class achievement-level markdown tables into JSON/CSV records."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


LEVELS = ("매우잘함", "잘함", "노력요함", "미응시")
CODE_RE = re.compile(r"\[([^\]]+)\]")


def clean_cell(value: str) -> str:
    value = value.strip()
    value = re.sub(r"<br\s*/?>", " ", value, flags=re.I)
    value = re.sub(r"\s+", " ", value)
    return value


def split_row(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return []
    return [clean_cell(part) for part in stripped.strip("|").split("|")]


def is_separator(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)


def parse_level(raw: str) -> tuple[str, bool]:
    raw = clean_cell(raw)
    inferred = "(추정)" in raw or "추정" in raw
    normalized = raw.replace("(추정)", "").replace("추정", "").strip()
    for level in LEVELS:
        if normalized == level or level in normalized:
            return level, inferred
    return normalized, inferred


def parse_assessment(header: str) -> tuple[str, str]:
    header = clean_cell(header)
    match = CODE_RE.search(header)
    code = match.group(1).strip() if match else ""
    assessment = CODE_RE.sub("", header).strip()
    return assessment, code


def iter_tables(lines: list[str]):
    subject = ""
    i = 0
    while i < len(lines):
        line = lines[i].rstrip("\n")
        heading = re.match(r"^##\s+(.+?)\s*$", line)
        if heading:
            subject = heading.group(1).strip()
            i += 1
            continue

        cells = split_row(line)
        if cells and cells[0] == "학생" and i + 1 < len(lines):
            sep = split_row(lines[i + 1])
            if not is_separator(sep):
                i += 1
                continue
            rows = []
            headers = cells
            i += 2
            while i < len(lines):
                row = split_row(lines[i])
                if not row or is_separator(row):
                    break
                rows.append(row)
                i += 1
            yield subject, headers, rows
            continue
        i += 1


def parse_markdown(path: Path) -> list[dict[str, object]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    records: list[dict[str, object]] = []
    for subject, headers, rows in iter_tables(lines):
        assessments = [parse_assessment(header) for header in headers[1:]]
        for row in rows:
            if len(row) < 2:
                continue
            student = row[0]
            for idx, raw in enumerate(row[1:]):
                if idx >= len(assessments):
                    continue
                assessment, code = assessments[idx]
                level, inferred = parse_level(raw)
                records.append(
                    {
                        "subject": subject,
                        "student": student,
                        "standard_code": code,
                        "assessment": assessment,
                        "level": level,
                        "inferred": inferred,
                        "raw_level": raw,
                    }
                )
    return records


def write_json(records: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(records: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["subject", "student", "standard_code", "assessment", "level", "inferred", "raw_level"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)


def print_summary(records: list[dict[str, object]]) -> None:
    by_subject = Counter(str(r["subject"]) for r in records)
    by_level = Counter(str(r["level"]) for r in records)
    inferred = sum(1 for r in records if r["inferred"])
    unknown = [r for r in records if r["level"] not in LEVELS]

    print(f"records: {len(records)}")
    print(f"students: {len({r['student'] for r in records})}")
    print(f"inferred: {inferred}")
    print("subjects:")
    for subject, count in sorted(by_subject.items()):
        print(f"  - {subject}: {count}")
    print("levels:")
    for level, count in by_level.most_common():
        print(f"  - {level}: {count}")
    if unknown:
        print("unknown levels:")
        for r in unknown[:20]:
            print(f"  - {r['subject']} / {r['student']} / {r['assessment']}: {r['raw_level']}")

    per_student = defaultdict(int)
    for r in records:
        per_student[str(r["student"])] += 1
    missing = [name for name, count in per_student.items() if count != max(per_student.values())]
    if missing:
        print(f"students with fewer records than max: {', '.join(missing)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Markdown 단계배정표 path")
    parser.add_argument("--json", type=Path, help="Output JSON path")
    parser.add_argument("--csv", type=Path, help="Output CSV path")
    parser.add_argument("--summary", action="store_true", help="Print summary")
    args = parser.parse_args()

    records = parse_markdown(args.input)
    if args.json:
        write_json(records, args.json)
    if args.csv:
        write_csv(records, args.csv)
    if args.summary or not (args.json or args.csv):
        print_summary(records)


if __name__ == "__main__":
    main()
