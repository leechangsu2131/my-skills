#!/usr/bin/env python3
"""Join verified inbox metadata to a raw capture without touching the archive."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import sys
import uuid


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def row_date_text(row: dict) -> str:
    return str(row.get("received_date") or row.get("received_at") or "")


def parse_archive_date(value: str) -> dt.date | dt.datetime:
    if len(value) == 10:
        return dt.date.fromisoformat(value)
    parsed = dt.datetime.fromisoformat(value)
    if parsed.tzinfo is not None:
        raise ValueError("archive dates must not include a UTC offset")
    return parsed


def archive_day(value: dt.date | dt.datetime) -> dt.date:
    return value.date() if isinstance(value, dt.datetime) else value


def strictly_newer(left: dt.date | dt.datetime, right: dt.date | dt.datetime) -> bool:
    if isinstance(left, dt.datetime) and isinstance(right, dt.datetime):
        return left > right
    return archive_day(left) > archive_day(right)


def strictly_older(left: dt.date | dt.datetime, right: dt.date | dt.datetime) -> bool:
    if isinstance(left, dt.datetime) and isinstance(right, dt.datetime):
        return left < right
    return archive_day(left) < archive_day(right)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a metadata-verified archive JSONL from raw capture plus CSV map."
    )
    parser.add_argument("raw_jsonl", type=pathlib.Path)
    parser.add_argument("metadata_csv", type=pathlib.Path)
    parser.add_argument("output_jsonl", type=pathlib.Path)
    parser.add_argument("--month", required=True, help="Target month in YYYY-MM form")
    parser.add_argument(
        "--markdown-output",
        type=pathlib.Path,
        help="Optionally write a new standalone Markdown archive; existing files are never overwritten.",
    )
    parser.add_argument(
        "--prepend-to",
        type=pathlib.Path,
        help="Prepend new records to a matching received-only archive after validating its date boundary.",
    )
    parser.add_argument(
        "--append-to",
        type=pathlib.Path,
        help="Append older records to a matching received-only archive after validating its date boundary.",
    )
    parser.add_argument(
        "--range-manifest",
        type=pathlib.Path,
        help="Write a small from/to record describing the verified message range.",
    )
    args = parser.parse_args()

    if sum(bool(value) for value in (args.markdown_output, args.prepend_to, args.append_to)) > 1:
        parser.error("choose only one of --markdown-output, --prepend-to, or --append-to")

    inputs = {args.raw_jsonl.resolve(), args.metadata_csv.resolve()}
    if args.output_jsonl.resolve() in inputs:
        parser.error("output_jsonl must differ from both input files")
    markdown_target = args.markdown_output or args.prepend_to or args.append_to
    if markdown_target:
        if markdown_target.resolve() in inputs | {args.output_jsonl.resolve()}:
            parser.error("markdown target must differ from both inputs and output_jsonl")
    if args.range_manifest:
        protected = inputs | {args.output_jsonl.resolve()}
        if markdown_target:
            protected.add(markdown_target.resolve())
        if args.range_manifest.resolve() in protected:
            parser.error("range manifest must have its own path")
    if args.markdown_output:
        if args.markdown_output.exists():
            parser.error(f"refusing to overwrite existing Markdown archive: {args.markdown_output}")

    try:
        target_month = dt.date.fromisoformat(f"{args.month}-01").strftime("%Y-%m")
    except ValueError:
        parser.error("--month must be YYYY-MM")

    raw_rows: dict[int, dict] = {}
    previous_sequence = 0
    with args.raw_jsonl.open("r", encoding="utf-8-sig", newline="") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                sequence = int(row["sequence"])
                body = row["body"]
                recorded_hash = row["body_sha256"]
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"raw JSONL line {line_number}: invalid row: {exc}") from exc
            if sequence != previous_sequence + 1:
                raise ValueError(
                    f"raw JSONL line {line_number}: sequence {sequence} does not follow {previous_sequence}"
                )
            if (
                not isinstance(body, str)
                or not isinstance(row.get("row_sha256"), str)
                or sha256(body) != recorded_hash
            ):
                raise ValueError(f"raw sequence {sequence}: invalid body SHA-256 or row fingerprint")
            raw_rows[sequence] = row
            previous_sequence = sequence

    metadata: dict[int, tuple[dt.date | dt.datetime, str]] = {}
    date_only_mode: bool | None = None
    with args.metadata_csv.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"sequence", "title"}
        has_date = bool(reader.fieldnames and "received_date" in reader.fieldnames)
        has_timestamp = bool(reader.fieldnames and "received_at" in reader.fieldnames)
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError("metadata CSV must have sequence and title columns")
        for line_number, row in enumerate(reader, start=2):
            try:
                sequence = int(row["sequence"])
                date_text = (row.get("received_date") or "").strip()
                timestamp_text = (row.get("received_at") or "").strip()
                if date_text and timestamp_text:
                    raise ValueError("provide only one of received_date or received_at per row")
                if date_text:
                    received: dt.date | dt.datetime = dt.date.fromisoformat(date_text)
                    this_date_only = True
                elif timestamp_text:
                    parsed = dt.datetime.fromisoformat(timestamp_text)
                    if parsed.tzinfo is not None:
                        raise ValueError("use local time without a UTC offset")
                    if len(timestamp_text) == 10:
                        received = parsed.date()
                        this_date_only = True
                    else:
                        received = parsed
                        this_date_only = False
                else:
                    raw_received = raw_rows.get(sequence, {}).get("received_date")
                    if raw_received:
                        received = dt.date.fromisoformat(raw_received)
                        this_date_only = True
                    else:
                        raw_timestamp = raw_rows.get(sequence, {}).get("received_at")
                        if not raw_timestamp:
                            raise ValueError("date is empty in CSV and raw row")
                        parsed = dt.datetime.fromisoformat(raw_timestamp)
                        if parsed.tzinfo is not None:
                            raise ValueError("use local time without a UTC offset")
                        if len(raw_timestamp) == 10:
                            received = parsed.date()
                            this_date_only = True
                        else:
                            received = parsed
                            this_date_only = False
                title = re.sub(r"[\r\n\t]+", " ", row["title"]).strip()
            except (TypeError, ValueError) as exc:
                raise ValueError(f"metadata CSV line {line_number}: invalid value: {exc}") from exc
            if date_only_mode is not None and this_date_only != date_only_mode:
                raise ValueError("metadata CSV cannot mix date-only rows and timestamp rows")
            date_only_mode = this_date_only
            if sequence in metadata:
                raise ValueError(f"metadata CSV line {line_number}: duplicate sequence {sequence}")
            if sequence not in raw_rows:
                raise ValueError(f"metadata CSV line {line_number}: no raw sequence {sequence}")
            if not title:
                raise ValueError(f"metadata CSV line {line_number}: empty title")
            metadata[sequence] = (received, title)

    if not metadata:
        raise ValueError("metadata CSV has no message rows")
    expected = list(range(1, max(metadata) + 1))
    if sorted(metadata) != expected:
        raise ValueError("metadata sequence must cover a contiguous prefix starting at 1")

    ordered_metadata = []
    previous_at: dt.date | dt.datetime | None = None
    for sequence in expected:
        received_at, title = metadata[sequence]
        if previous_at is not None and received_at > previous_at:
            raise ValueError(f"metadata dates move newer at sequence {sequence}")
        previous_at = received_at
        ordered_metadata.append((sequence, received_at, title))

    selected = [item for item in ordered_metadata if item[1].strftime("%Y-%m") == target_month]
    if not selected:
        raise ValueError(f"metadata CSV has no messages in target month {target_month}")

    output_rows = []
    for sequence, received_at, title in selected:
        raw = raw_rows[sequence]
        date_value = received_at.isoformat(timespec="seconds") if isinstance(received_at, dt.datetime) else received_at.isoformat()
        output_rows.append({
            ("received_at" if isinstance(received_at, dt.datetime) else "received_date"): date_value,
            "title": title,
            "body": raw["body"],
            "capture_sequence": sequence,
            "row_sha256": raw["row_sha256"],
            "body_sha256": raw["body_sha256"],
        })

    serialized = "".join(
        json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
        for row in output_rows
    )
    payload = serialized.encode("utf-8")
    range_manifest = None
    if args.range_manifest:
        def describe_range_record(row: dict) -> dict:
            preview = re.sub(r"\s+", " ", row["body"]).strip()
            date_key = "received_at" if "received_at" in row else "received_date"
            return {
                "capture_sequence": row["capture_sequence"],
                date_key: row[date_key],
                "sender": row["title"],
                "body_preview": preview[:120],
                "row_sha256": row["row_sha256"],
                "body_sha256": row["body_sha256"],
            }

        range_manifest = {
            "schema_version": 1,
            "scope": "gbetalk-received-inbox",
            "month": target_month,
            "record_count": len(output_rows),
            "newest": describe_range_record(output_rows[0]),
            "oldest": describe_range_record(output_rows[-1]),
            "verified_jsonl_sha256": hashlib.sha256(payload).hexdigest(),
        }

    markdown = None
    existing_bytes = None
    existing_digest = None
    newline = "\n"
    if args.markdown_output:
        markdown = "\n\n".join(
            f"## {row.get('received_date', row.get('received_at', '').replace('T', ' '))} — {row['title']}\n\n{row['body'].strip()}"
            for row in output_rows
        ) + "\n"
    elif args.prepend_to or args.append_to:
        archive_path = args.prepend_to or args.append_to
        existing_bytes = archive_path.read_bytes()
        existing_text = existing_bytes.decode("utf-8-sig")
        newline = "\r\n" if b"\r\n" in existing_bytes else "\n"
        header_pattern = re.compile(r"(?m)^## (\d{4}-\d{2}-\d{2}(?: \d{2}:\d{2}:\d{2})?) — (.*?)\r?$")
        headers = list(header_pattern.finditer(existing_text))
        if not headers:
            raise ValueError(f"existing archive has no recognized records: {archive_path}")
        existing_times = [parse_archive_date(match.group(1)) for match in headers]
        for earlier, later in zip(existing_times, existing_times[1:]):
            if strictly_newer(later, earlier):
                raise ValueError("existing archive is not ordered newest-to-oldest; refusing to merge")
            if archive_day(earlier) == archive_day(later) and type(earlier) is not type(later):
                raise ValueError("existing archive mixes date-only and timestamp records on the same day; refusing to merge")
        if args.prepend_to:
            latest_existing = existing_times[0]
            if any(not strictly_newer(parse_archive_date(row_date_text(row)), latest_existing) for row in output_rows):
                raise ValueError(
                    f"every new record must be newer than existing archive head {headers[0].group(1)}"
                )
        else:
            oldest_existing = existing_times[-1]
            if any(not strictly_older(parse_archive_date(row_date_text(row)), oldest_existing) for row in output_rows):
                raise ValueError(
                    f"every appended record must be older than existing archive tail {headers[-1].group(1)}"
                )

        record_pattern = re.compile(
            r"(?ms)^## (\d{4}-\d{2}-\d{2}(?: \d{2}:\d{2}:\d{2})?) — (.*?)\r?\n\r?\n(.*?)(?=^## |\Z)"
        )
        existing_keys = set()
        for match in record_pattern.finditer(existing_text):
            existing_keys.add((
                match.group(1),
                match.group(2).strip(),
                sha256(match.group(3).strip().replace("\r\n", "\n")),
            ))
        for row in output_rows:
            key = (
                row_date_text(row).replace("T", " "),
                row["title"],
                sha256(row["body"].strip().replace("\r\n", "\n")),
            )
            if key in existing_keys:
                raise ValueError(f"new record already exists in archive: {key[0]} — {key[1]}")

        newline_text = newline
        rendered_blocks = []
        for row in output_rows:
            body = row["body"].strip().replace("\r\n", "\n").replace("\r", "\n")
            body = body.replace("\n", newline_text)
            rendered_blocks.append(
                f"## {row_date_text(row).replace('T', ' ')} — {row['title']}"
                f"{newline_text}{newline_text}{body}"
            )
        rendered_new = (newline_text * 2).join(rendered_blocks) + newline_text * 2
        markdown = (
            rendered_new + existing_text
            if args.prepend_to
            else existing_text.rstrip("\r\n") + newline_text * 2 + rendered_new
        )
        existing_digest = hashlib.sha256(existing_bytes).hexdigest()

    range_manifest_bytes = None
    if args.range_manifest and range_manifest is not None:
        range_manifest_bytes = (json.dumps(range_manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        if args.range_manifest.exists() and args.range_manifest.read_bytes() != range_manifest_bytes:
            raise ValueError(f"range manifest already exists with different contents: {args.range_manifest}")

    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    args.output_jsonl.write_bytes(payload)
    if args.markdown_output and markdown is not None:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(markdown, encoding="utf-8", newline="\n")
    elif (args.prepend_to or args.append_to) and markdown is not None and existing_bytes is not None:
        archive_path = args.prepend_to or args.append_to
        temp_path = archive_path.with_name(f".{archive_path.name}.{uuid.uuid4().hex}.tmp")
        merged_bytes = markdown.encode("utf-8")
        with temp_path.open("xb") as stream:
            stream.write(merged_bytes)
            stream.flush()
            os.fsync(stream.fileno())
        if hashlib.sha256(archive_path.read_bytes()).hexdigest() != existing_digest:
            raise RuntimeError("existing archive changed while merging; original file was not replaced")
        os.replace(temp_path, archive_path)
        if archive_path.read_bytes() != merged_bytes:
            raise RuntimeError("merged archive verification failed after replacement")
    if args.range_manifest and range_manifest_bytes is not None and not args.range_manifest.exists():
        args.range_manifest.parent.mkdir(parents=True, exist_ok=True)
        temp_path = args.range_manifest.with_name(f".{args.range_manifest.name}.{uuid.uuid4().hex}.tmp")
        with temp_path.open("xb") as stream:
            stream.write(range_manifest_bytes)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, args.range_manifest)
    first = row_date_text(output_rows[0])
    last = row_date_text(output_rows[-1])
    print(
        f"Wrote {len(output_rows)} verified rows ({first} through {last}); "
        f"SHA-256 {hashlib.sha256(payload).hexdigest()}"
    )
    if args.markdown_output:
        print(f"Wrote standalone Markdown archive: {args.markdown_output}")
    if args.prepend_to:
        print(f"Prepended {len(output_rows)} records to received archive: {args.prepend_to}")
    if args.append_to:
        print(f"Appended {len(output_rows)} records to received archive: {args.append_to}")
    if args.range_manifest:
        print(f"Wrote verified message range: {args.range_manifest}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)
