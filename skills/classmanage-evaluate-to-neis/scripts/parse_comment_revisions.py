#!/usr/bin/env python3
"""Parse NEIS subject comment revision markdown files into JSON."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


SUBJECT_HINTS = {
    "\uad6d\uc5b4": "\uad6d\uc5b4",
    "\uc218\ud559": "\uc218\ud559",
    "\uc0ac\ud68c": "\uc0ac\ud68c",
    "\ub3c4\ub355": "\ub3c4\ub355",
    "\ubbf8\uc220": "\ubbf8\uc220",
    "\uc74c\uc545": "\uc74c\uc545",
}

KEEP = "\uc720\uc9c0"
MODIFY = "\uc218\uc815"
CRITERIA_HEADING = "\uc791\uc131 \uae30\uc900"


def split_markdown_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def subject_from_filename(path: Path) -> str | None:
    name = path.name
    for hint, subject in SUBJECT_HINTS.items():
        if hint in name:
            return subject
    return None


def parse_file(path: Path) -> list[dict[str, object]]:
    text = path.read_text(encoding="utf-8")
    default_subject = subject_from_filename(path)
    current_subject: str | None = default_subject
    records: list[dict[str, object]] = []

    for line in text.splitlines():
        if line.startswith("## "):
            heading = line[3:].strip()
            if heading != CRITERIA_HEADING:
                current_subject = heading
            continue

        if not line.startswith("|"):
            continue
        cells = split_markdown_row(line)
        if not cells or cells[0] in {"\ubc88\ud638", "---"} or cells[0].startswith("---"):
            continue
        if not cells[0].isdigit():
            continue

        if len(cells) >= 4:
            status = cells[2].replace("*", "").strip()
            comment = cells[3].strip()
            if status == MODIFY and comment:
                records.append(
                    {
                        "subject": current_subject,
                        "number": int(cells[0]),
                        "student": cells[1],
                        "comment": comment,
                        "source": path.name,
                        "mode": "modify_only",
                    }
                )
        elif len(cells) >= 3 and default_subject:
            records.append(
                {
                    "subject": default_subject,
                    "number": int(cells[0]),
                    "student": cells[1],
                    "comment": cells[2].strip(),
                    "source": path.name,
                    "mode": "full_table",
                }
            )

    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--json", required=True, type=Path)
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()

    records: list[dict[str, object]] = []
    for path in sorted(args.data_dir.glob("*.md")):
        records.extend(parse_file(path))

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.summary:
        print(f"records: {len(records)}")
        for subject, count in sorted(Counter(str(r["subject"]) for r in records).items()):
            print(f"  - {subject}: {count}")
        for record in records[:10]:
            print(
                f"{record['subject']} {record['number']} {record['student']}: "
                f"{str(record['comment'])[:60]}"
            )


if __name__ == "__main__":
    main()
