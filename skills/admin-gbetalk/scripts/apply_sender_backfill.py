#!/usr/bin/env python3
"""Create sender-enriched JSONL copies from fingerprint-verified metadata."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import sys
import uuid


HEX_SHA256 = re.compile(r"^[a-f0-9]{64}$")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_jsonl(path: pathlib.Path) -> tuple[bytes, list[dict]]:
    data = path.read_bytes()
    if not data or not data.endswith(b"\n"):
        raise ValueError(f"{path}: empty input or missing final newline")
    rows = []
    for line_number, line in enumerate(data.splitlines(), start=1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{line_number}: each line must be a JSON object")
        rows.append(row)
    return data, rows


def date_of(row: dict, where: str) -> str | None:
    value = row.get("received_date")
    if value:
        date = value
    else:
        value = row.get("received_at")
        if not value:
            return None
        if isinstance(value, dt.datetime):
            date = value.date().isoformat()
        elif isinstance(value, str) and len(value) >= 10:
            date = value[:10]
        else:
            raise ValueError(f"{where}: invalid received_at {value!r}")
    if not isinstance(date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        raise ValueError(f"{where}: expected a YYYY-MM-DD message date, got {date!r}")
    try:
        dt.date.fromisoformat(date)
    except ValueError as exc:
        raise ValueError(f"{where}: invalid calendar date {date!r}") from exc
    return date


def validate_source(rows: list[dict], path: pathlib.Path) -> None:
    for index, row in enumerate(rows, start=1):
        where = f"{path}:sequence {index}"
        if row.get("sequence") != index:
            raise ValueError(f"{where}: sequences must be contiguous and 1-based")
        for field in ("row_sha256", "body_sha256"):
            value = row.get(field)
            if not isinstance(value, str) or not HEX_SHA256.fullmatch(value):
                raise ValueError(f"{where}: invalid {field}")
        body = row.get("body")
        if not isinstance(body, str) or sha256(body.encode("utf-8")) != row["body_sha256"]:
            raise ValueError(f"{where}: body hash mismatch")


def fingerprint_key(row: dict, date: str) -> tuple[str, str, str]:
    return row["row_sha256"], row["body_sha256"], date


def verified_sender(record: dict, where: str) -> str:
    sender = record.get("sender")
    title = record.get("title")
    if sender and title and sender != title:
        raise ValueError(f"{where}: sender and title disagree")
    value = sender or title
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{where}: missing sender/title")
    value = value.strip()
    if "\n" in value or "\r" in value:
        raise ValueError(f"{where}: sender contains a line break")
    return value


def add_verified_metadata(
    metadata_path: pathlib.Path,
    target_index: dict[tuple[str, str, str], list[int]],
    assignments: dict[int, dict],
) -> int:
    _, records = read_jsonl(metadata_path)
    matched = 0
    for line_number, record in enumerate(records, start=1):
        where = f"{metadata_path}:{line_number}"
        if not record.get("sender") and not record.get("title"):
            continue
        date = date_of(record, where)
        if date is None:
            raise ValueError(f"{where}: no received date to disambiguate repeated bodies")
        sender = verified_sender(record, where)
        key = fingerprint_key(record, date)
        candidates = target_index.get(key, [])
        if len(candidates) != 1:
            raise ValueError(
                f"{where}: expected one source row for hash/date tuple; found {candidates}"
            )
        sequence = candidates[0]
        matched += 1
        prior = assignments.get(sequence)
        evidence = {
            "sender": sender,
            "verification_method": "previously-verified-metadata-exact-row-body-date-join",
            "evidence_file": str(metadata_path),
            "evidence_line": line_number,
        }
        if prior and prior["sender"] != sender:
            raise ValueError(f"{where}: sender conflicts at source sequence {sequence}")
        if not prior:
            assignments[sequence] = evidence
    return matched


def load_manual_map(
    map_path: pathlib.Path,
    source_path: pathlib.Path,
    source_data: bytes,
    rows: list[dict],
    assignments: dict[int, dict],
) -> int:
    mapping = json.loads(map_path.read_text(encoding="utf-8-sig"))
    if mapping.get("source_file_sha256") != sha256(source_data):
        raise ValueError(f"{map_path}: source file SHA-256 does not match input")
    if pathlib.Path(mapping.get("source_path", "")).resolve() != source_path.resolve():
        raise ValueError(f"{map_path}: source path does not match input")
    if mapping.get("total_rows") != len(rows) or not isinstance(mapping.get("records"), list):
        raise ValueError(f"{map_path}: source row count or records list is invalid")

    seen: set[int] = set()
    for record in mapping["records"]:
        sequence = record.get("sequence")
        if not isinstance(sequence, int) or not 1 <= sequence <= len(rows) or sequence in seen:
            raise ValueError(f"{map_path}: invalid or duplicate sequence {sequence!r}")
        seen.add(sequence)
        source = rows[sequence - 1]
        if (record.get("row_sha256") != source["row_sha256"]
                or record.get("body_sha256") != source["body_sha256"]):
            raise ValueError(f"{map_path}: sequence {sequence} fingerprint mismatch")
        source_date = date_of(source, f"{source_path}:sequence {sequence}")
        if not source_date or record.get("received_date") != source_date:
            raise ValueError(f"{map_path}: sequence {sequence} date mismatch")
        sender = verified_sender(record, f"{map_path}:sequence {sequence}")
        method = record.get("verification_method")
        if not isinstance(method, str) or not method.strip():
            raise ValueError(f"{map_path}: sequence {sequence} has no verification method")
        if not (record.get("manually_verified") is True
                or record.get("verification_status") == "verified-visible-header"):
            raise ValueError(f"{map_path}: sequence {sequence} is not marked as visually verified")
        prior = assignments.get(sequence)
        if prior and prior["sender"] != sender:
            raise ValueError(f"{map_path}: sender conflicts at sequence {sequence}")
        if not prior:
            assignments[sequence] = {
                "sender": sender,
                "verification_method": method,
                "verification_status": "verified-visible-header",
                "manually_verified": True,
                "evidence_file": str(map_path),
                "visible_header": record.get("visible_header"),
                "visible_list_label": record.get("visible_list_label"),
                "visible_body_check": record.get("visible_body_check"),
                "search_result_count": record.get("search_result_count"),
                "search_query": record.get("search_query"),
                "verified_at": record.get("verified_at"),
            }
    return len(seen)


def atomic_create(path: pathlib.Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temp_path.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temp_path, path)
    finally:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass


def sequence_ranges(values: list[int]) -> list[str]:
    if not values:
        return []
    ranges = []
    start = previous = values[0]
    for value in values[1:]:
        if value == previous + 1:
            previous = value
            continue
        ranges.append(str(start) if start == previous else f"{start}-{previous}")
        start = previous = value
    ranges.append(str(start) if start == previous else f"{start}-{previous}")
    return ranges


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Write a sender-enriched JSONL copy; never modify the source."
    )
    parser.add_argument("source_jsonl", type=pathlib.Path)
    parser.add_argument("output_jsonl", type=pathlib.Path)
    parser.add_argument("--verified-metadata", action="append", default=[], type=pathlib.Path)
    parser.add_argument("--manual-map", type=pathlib.Path)
    args = parser.parse_args()

    source_path = args.source_jsonl.resolve()
    output_path = args.output_jsonl.resolve()
    metadata_paths = [path.resolve() for path in args.verified_metadata]
    manual_map_path = args.manual_map.resolve() if args.manual_map else None
    inputs = {source_path, *metadata_paths}
    if manual_map_path:
        inputs.add(manual_map_path)
    if output_path in inputs:
        parser.error("output_jsonl must differ from every input file")

    try:
        source_data, rows = read_jsonl(source_path)
        validate_source(rows, source_path)
        target_index: dict[tuple[str, str, str], list[int]] = {}
        assignments: dict[int, dict] = {}
        for sequence, row in enumerate(rows, start=1):
            date = date_of(row, f"{source_path}:sequence {sequence}")
            if date:
                target_index.setdefault(fingerprint_key(row, date), []).append(sequence)
            existing = row.get("sender")
            if existing:
                assignments[sequence] = {
                    "sender": verified_sender(row, f"{source_path}:sequence {sequence}"),
                    "verification_method": row.get("sender_evidence", {}).get(
                        "verification_method", "existing-source-sender"
                    ) if isinstance(row.get("sender_evidence"), dict) else "existing-source-sender",
                    "evidence_file": str(source_path),
                }

        metadata_counts = {}
        for metadata_path in metadata_paths:
            metadata_counts[str(metadata_path)] = add_verified_metadata(
                metadata_path, target_index, assignments
            )

        manual_count = 0
        if manual_map_path:
            manual_count = load_manual_map(
                manual_map_path, source_path, source_data, rows, assignments
            )

        output_lines = []
        missing = []
        for sequence, source in enumerate(rows, start=1):
            enriched = dict(source)
            evidence = assignments.get(sequence)
            if evidence:
                enriched["sender"] = evidence["sender"]
                enriched["sender_capture_status"] = "verified"
                enriched["sender_evidence"] = {
                    key: value for key, value in evidence.items() if key != "sender"
                }
            else:
                enriched.pop("sender", None)
                enriched["sender_capture_status"] = "missing"
                missing.append(sequence)
            output_lines.append(json.dumps(enriched, ensure_ascii=False, separators=(",", ":")))

        output_data = ("\n".join(output_lines) + "\n").encode("utf-8")
        atomic_create(output_path, output_data)
        summary = {
            "status": "complete-with-gaps" if missing else "complete",
            "source": str(source_path),
            "source_sha256": sha256(source_data),
            "output": str(output_path),
            "output_sha256": sha256(output_data),
            "records": len(rows),
            "sender_count": len(rows) - len(missing),
            "missing_sender_count": len(missing),
            "missing_sender_sequence_ranges": sequence_ranges(missing),
            "verified_metadata_rows": metadata_counts,
            "manual_map_rows": manual_count,
        }
        print(json.dumps(summary, ensure_ascii=False))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
