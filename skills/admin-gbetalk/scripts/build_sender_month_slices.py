#!/usr/bin/env python3
"""Build date-partitioned sender-status copies without changing captured sources."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from datetime import date
from pathlib import Path


MONTHS = ("2026-08", "2026-09", "2026-10")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_jsonl(path: Path) -> tuple[bytes, list[dict]]:
    raw = path.read_bytes()
    records = []
    for line_number, line in enumerate(raw.splitlines(), 1):
        try:
            record = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"{path}:{line_number}: invalid UTF-8 JSONL: {exc}") from exc
        if not isinstance(record, dict):
            raise ValueError(f"{path}:{line_number}: expected a JSON object")
        body = record.get("body")
        if not isinstance(body, str):
            raise ValueError(f"{path}:{line_number}: body is missing")
        if record.get("body_sha256") != sha256(body.encode("utf-8")):
            raise ValueError(f"{path}:{line_number}: body_sha256 mismatch")
        if not SHA256_RE.fullmatch(str(record.get("row_sha256", ""))):
            raise ValueError(f"{path}:{line_number}: invalid row_sha256")
        if not SHA256_RE.fullmatch(str(record.get("body_sha256", ""))):
            raise ValueError(f"{path}:{line_number}: invalid body_sha256")
        try:
            received_date = date.fromisoformat(record.get("received_date", ""))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{path}:{line_number}: invalid received_date") from exc
        if not isinstance(record.get("sequence"), int) or record["sequence"] < 1:
            raise ValueError(f"{path}:{line_number}: invalid sequence")
        record["_partition_date"] = received_date.isoformat()
        records.append(record)
    return raw, records


def has_sender(record: dict) -> bool:
    return any(isinstance(record.get(key), str) and record[key].strip() for key in ("sender", "title"))


def write_jsonl(path: Path, records: list[dict]) -> str:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        for record in records:
            output = {key: value for key, value in record.items() if not key.startswith("_")}
            handle.write(json.dumps(output, ensure_ascii=False, separators=(",", ":")) + "\n")
    return sha256(path.read_bytes())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("october_sender_jsonl", type=Path)
    parser.add_argument("older_sender_jsonl", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument(
        "--new-october-jsonl",
        type=Path,
        help="Optional newly verified October messages; this source is placed first within each date.",
    )
    args = parser.parse_args()

    if args.output_dir.exists():
        raise SystemExit(f"output directory already exists; refusing to overwrite: {args.output_dir}")
    args.output_dir.mkdir(parents=True)

    sources = []
    if args.new_october_jsonl:
        sources.append(("october-live-capture", args.new_october_jsonl, 0))
    sources.extend([
        ("october-sender-backfill", args.october_sender_jsonl, 1 if args.new_october_jsonl else 0),
        ("older-sender-backfill", args.older_sender_jsonl, 2 if args.new_october_jsonl else 1),
    ])
    source_audit = {}
    by_month: dict[str, list[dict]] = defaultdict(list)
    seen_fingerprints = set()

    for source_name, path, source_rank in sources:
        raw, records = load_jsonl(path)
        source_audit[source_name] = {
            "path": str(path),
            "sha256": sha256(raw),
            "record_count": len(records),
        }
        source_sequences = set()
        for record in records:
            sequence = record["sequence"]
            if sequence in source_sequences:
                raise SystemExit(f"duplicate sequence {sequence} in {path}")
            source_sequences.add(sequence)
            month = record["_partition_date"][:7]
            if month not in MONTHS:
                continue
            fingerprint = (
                record["row_sha256"], record["body_sha256"], record["_partition_date"]
            )
            if fingerprint in seen_fingerprints:
                raise SystemExit(f"duplicate row/body/date across source files: {fingerprint}")
            seen_fingerprints.add(fingerprint)
            record["backfill_source"] = source_name
            record["backfill_source_sequence"] = sequence
            if not has_sender(record):
                record["sender"] = None
                record["sender_capture_status"] = "missing"
            elif not record.get("sender_capture_status") and isinstance(record.get("sender_evidence"), dict):
                record["sender_capture_status"] = "verified-visible-header"
            elif not record.get("sender_capture_status"):
                record["sender_capture_status"] = "verified-existing-source"
            record["_source_rank"] = source_rank
            by_month[month].append(record)

    month_audit = {}
    for month in MONTHS:
        records = sorted(
            by_month.get(month, []),
            key=lambda record: (
                record["_partition_date"], record["_source_rank"], record["sequence"]
            ),
            reverse=False,
        )
        # Dates sort newest first; within a date put the newest live capture
        # first, then preserve each source's original capture order. Message
        # times are intentionally absent, so cross-source order is not asserted.
        records.sort(
            key=lambda record: (
                record["_partition_date"], -record["_source_rank"], -record["sequence"]
            ),
            reverse=True,
        )
        output_path = args.output_dir / f"received-{month}-sender-status.jsonl"
        output_sha = write_jsonl(output_path, records)
        sender_count = sum(has_sender(record) for record in records)
        missing_count = len(records) - sender_count
        month_audit[month] = {
            "output_path": output_path.name,
            "output_sha256": output_sha,
            "record_count": len(records),
            "sender_count": sender_count,
            "missing_sender_count": missing_count,
            "newest_date": max((r["_partition_date"] for r in records), default=None),
            "oldest_date": min((r["_partition_date"] for r in records), default=None),
            "source_counts": {
                source_name: sum(r["backfill_source"] == source_name for r in records)
                for source_name, _, _ in sources
            },
        }

    audit = {
        "schema_version": 1,
        "months": list(MONTHS),
        "sources": source_audit,
        "month_slices": month_audit,
        "total_records": sum(entry["record_count"] for entry in month_audit.values()),
        "total_senders": sum(entry["sender_count"] for entry in month_audit.values()),
        "total_missing_senders": sum(entry["missing_sender_count"] for entry in month_audit.values()),
        "ordering_note": "Records are ordered by received_date descending, then source priority and source sequence descending. Message times are not available, so cross-source ordering within one date is not asserted.",
        "note": "Sender fields are preserved only when present in a fingerprint-verified source; missing values are not inferred. Directly verified live captures retain visible-header evidence.",
    }
    audit_path = args.output_dir / "sender-month-slices-audit.json"
    with audit_path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(audit, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
