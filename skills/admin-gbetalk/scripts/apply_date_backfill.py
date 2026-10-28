#!/usr/bin/env python3
"""Create a date-enriched JSONL copy from immutable raw captures and verified maps."""

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


def valid_date(value: object, where: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError(f"{where}: expected YYYY-MM-DD, got {value!r}")
    try:
        dt.date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{where}: invalid calendar date {value!r}") from exc
    return value


def message_date(row: dict, where: str) -> str | None:
    value = row.get("received_date")
    if value:
        return valid_date(value, where)
    value = row.get("received_at")
    if value:
        if not isinstance(value, str) or len(value) < 10:
            raise ValueError(f"{where}: invalid received_at {value!r}")
        return valid_date(value[:10], where)
    return None


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


def validate_raw(rows: list[dict], path: pathlib.Path) -> None:
    for index, row in enumerate(rows, start=1):
        where = f"{path}:sequence {index}"
        if row.get("sequence") != index:
            raise ValueError(f"{where}: sequences must be contiguous and 1-based")
        row_sha = row.get("row_sha256")
        body_sha = row.get("body_sha256")
        body = row.get("body")
        if not isinstance(row_sha, str) or not HEX_SHA256.fullmatch(row_sha):
            raise ValueError(f"{where}: invalid row_sha256")
        if not isinstance(body_sha, str) or not HEX_SHA256.fullmatch(body_sha):
            raise ValueError(f"{where}: invalid body_sha256")
        if not isinstance(body, str) or sha256(body.encode("utf-8")) != body_sha:
            raise ValueError(f"{where}: body hash mismatch")


def load_date_map(path: pathlib.Path, raw_path: pathlib.Path, raw_data: bytes,
                  rows: list[dict]) -> dict[int, tuple[str, str]]:
    mapping = json.loads(path.read_text(encoding="utf-8-sig"))
    if mapping.get("source_file_sha256") != sha256(raw_data):
        raise ValueError(f"{path}: source file SHA-256 does not match raw input")
    mapped_path = pathlib.Path(mapping.get("source_path", "")).resolve()
    if mapped_path != raw_path.resolve():
        raise ValueError(f"{path}: source path does not match raw input")
    if mapping.get("total_rows") != len(rows) or not isinstance(mapping.get("records"), list):
        raise ValueError(f"{path}: source row count or records list is invalid")

    result: dict[int, tuple[str, str]] = {}
    for record in mapping["records"]:
        sequence = record.get("sequence")
        if not isinstance(sequence, int) or not 1 <= sequence <= len(rows) or sequence in result:
            raise ValueError(f"{path}: invalid or duplicate sequence {sequence!r}")
        source = rows[sequence - 1]
        if (record.get("row_sha256") != source["row_sha256"]
                or record.get("body_sha256") != source["body_sha256"]):
            raise ValueError(f"{path}: sequence {sequence} fingerprint mismatch")
        date = valid_date(record.get("received_date"), f"{path}:sequence {sequence}")
        method = record.get("verification_method")
        if not isinstance(method, str) or not method:
            raise ValueError(f"{path}: sequence {sequence} has no verification method")
        result[sequence] = (date, method)
    return result


def load_verified_metadata(path: pathlib.Path, rows: list[dict]) -> dict[int, tuple[str, str]]:
    _, records = read_jsonl(path)
    result: dict[int, tuple[str, str]] = {}
    for line_number, record in enumerate(records, start=1):
        sequence = record.get("capture_sequence", record.get("sequence"))
        if not isinstance(sequence, int) or not 1 <= sequence <= len(rows) or sequence in result:
            raise ValueError(f"{path}:{line_number}: invalid or duplicate capture sequence")
        source = rows[sequence - 1]
        if (record.get("row_sha256") != source["row_sha256"]
                or record.get("body_sha256") != source["body_sha256"]):
            raise ValueError(f"{path}:{line_number}: sequence {sequence} fingerprint mismatch")
        date = message_date(record, f"{path}:sequence {sequence}")
        if date is None:
            raise ValueError(f"{path}:sequence {sequence} has no message date")
        result[sequence] = (date, "verified-metadata")
    return result


def atomic_create(path: pathlib.Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temp_path.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        # Hard-link creation fails if the destination already exists.
        os.link(temp_path, path)
    finally:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Write a new date-enriched JSONL copy; never modify the raw input."
    )
    parser.add_argument("raw_jsonl", type=pathlib.Path)
    parser.add_argument("output_jsonl", type=pathlib.Path)
    parser.add_argument("--verified-metadata", type=pathlib.Path)
    parser.add_argument("--date-map", action="append", default=[], type=pathlib.Path)
    args = parser.parse_args()
    raw_path = args.raw_jsonl.resolve()
    output_path = args.output_jsonl.resolve()
    inputs = {raw_path}
    if args.verified_metadata:
        inputs.add(args.verified_metadata.resolve())
    inputs.update(path.resolve() for path in args.date_map)
    if output_path in inputs:
        parser.error("output_jsonl must differ from every input file")

    try:
        raw_data, rows = read_jsonl(raw_path)
        validate_raw(rows, raw_path)
        dates: dict[int, tuple[str, str]] = {}
        for sequence, row in enumerate(rows, start=1):
            existing = message_date(row, f"{raw_path}:sequence {sequence}")
            if existing:
                dates[sequence] = (existing, "raw-metadata")
        if args.verified_metadata:
            for sequence, value in load_verified_metadata(args.verified_metadata, rows).items():
                if sequence in dates and dates[sequence][0] != value[0]:
                    raise ValueError(f"verified metadata conflicts with raw date at sequence {sequence}")
                dates[sequence] = value
        for map_path in args.date_map:
            for sequence, value in load_date_map(map_path, raw_path, raw_data, rows).items():
                if sequence in dates and dates[sequence][0] != value[0]:
                    raise ValueError(f"date map conflicts with another date at sequence {sequence}")
                dates[sequence] = value

        missing = [sequence for sequence in range(1, len(rows) + 1) if sequence not in dates]
        if missing:
            preview = ", ".join(map(str, missing[:20]))
            raise ValueError(f"refusing incomplete output: {len(missing)} missing dates (sequences {preview})")

        output_lines = []
        for sequence, source in enumerate(rows, start=1):
            enriched = dict(source)
            enriched["received_date"] = dates[sequence][0]
            output_lines.append(json.dumps(enriched, ensure_ascii=False, separators=(",", ":")))
        output_data = ("\n".join(output_lines) + "\n").encode("utf-8")
        atomic_create(output_path, output_data)
        print(json.dumps({
            "status": "complete",
            "source": str(raw_path),
            "source_sha256": sha256(raw_data),
            "output": str(output_path),
            "output_sha256": sha256(output_data),
            "records": len(rows),
            "received_date_count": len(dates),
            "date_only": True,
        }, ensure_ascii=False))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
