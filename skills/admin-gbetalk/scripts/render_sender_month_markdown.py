#!/usr/bin/env python3
"""Render verified monthly sender-status JSONL slices as readable Markdown."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date
from pathlib import Path


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def code_fence(text: str) -> str:
    runs = [len(match.group(0)) for match in re.finditer(r"~+", text)]
    return "~" * max(3, max(runs, default=0) + 1)


def read_and_validate(month: str, source: Path, expected: dict) -> list[dict]:
    raw = source.read_bytes()
    if sha256(raw) != expected.get("output_sha256"):
        raise ValueError(f"{source}: SHA-256 does not match sender-month-slices-audit.json")
    records = []
    previous_date = None
    for line_number, line in enumerate(raw.splitlines(), 1):
        try:
            row = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"{source}:{line_number}: invalid JSONL: {exc}") from exc
        if not isinstance(row, dict) or not isinstance(row.get("body"), str):
            raise ValueError(f"{source}:{line_number}: missing object/body")
        received_date = row.get("received_date")
        try:
            parsed_date = date.fromisoformat(received_date)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{source}:{line_number}: invalid received_date") from exc
        if parsed_date.strftime("%Y-%m") != month:
            raise ValueError(f"{source}:{line_number}: row does not belong to {month}")
        if previous_date is not None and parsed_date > previous_date:
            raise ValueError(f"{source}:{line_number}: records are not newest-to-oldest by date")
        previous_date = parsed_date
        if not SHA256_RE.fullmatch(str(row.get("row_sha256", ""))):
            raise ValueError(f"{source}:{line_number}: invalid row_sha256")
        if row.get("body_sha256") != sha256(row["body"].encode("utf-8")):
            raise ValueError(f"{source}:{line_number}: body_sha256 mismatch")
        if not isinstance(row.get("backfill_source_sequence"), int):
            raise ValueError(f"{source}:{line_number}: missing source sequence")
        has_sender = isinstance(row.get("sender"), str) and bool(row["sender"].strip())
        if not has_sender and row.get("sender_capture_status") != "missing":
            raise ValueError(f"{source}:{line_number}: missing sender is not explicitly marked")
        records.append(row)

    if len(records) != expected.get("record_count"):
        raise ValueError(f"{source}: record count does not match audit")
    sender_count = sum(isinstance(row.get("sender"), str) and bool(row["sender"].strip()) for row in records)
    if sender_count != expected.get("sender_count"):
        raise ValueError(f"{source}: sender count does not match audit")
    return records


def render_month(month: str, rows: list[dict], summary: dict, source_sha256: str) -> str:
    year, month_number = map(int, month.split("-"))
    oldest = summary.get("oldest_date") or "-"
    newest = summary.get("newest_date") or "-"
    sender_count = summary["sender_count"]
    missing_count = summary["missing_sender_count"]
    lines = [
        f"# {year}년 {month_number}월 받은 쪽지",
        "",
        f"- 메시지 수: {len(rows)}건",
        f"- 발신자 확인: {sender_count}건 / 미확인: {missing_count}건",
        f"- 날짜 범위: {oldest} ~ {newest}",
        "- 날짜 내 정렬은 날짜만 기준으로 합니다. 발신 시각이 없는 항목의 같은 날짜 안 정확한 순서는 보증하지 않습니다.",
        "- 범위: 현재 확보한 검증 캡처 기록입니다. 앱 받은쪽지함 전체 기간이 빠짐없이 포함됐는지는 확인되지 않았습니다.",
        f"- 월별 JSONL SHA-256: `{source_sha256}`",
        "- 첨부파일과 사진은 저장하지 않았습니다.",
        "",
        "---",
        "",
    ]
    for row in rows:
        sender = row.get("sender")
        if isinstance(sender, str) and sender.strip():
            sender_label = f"{sender.strip()} (확인됨)"
        else:
            sender_label = "발신자 미확인"
        lines.extend([
            f"## {row['received_date']} — {sender_label}",
            "",
            f"- 원본: `{row.get('backfill_source', 'unknown')}` 순번 {row['backfill_source_sequence']}",
            f"- 행 SHA-256: `{row['row_sha256']}`",
            f"- 본문 SHA-256: `{row['body_sha256']}`",
            "",
        ])
        fence = code_fence(row["body"])
        lines.extend([fence, row["body"], fence, "", "---", ""])
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("month_slice_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--months", nargs="+", help="Months to render (default: every month in audit)")
    args = parser.parse_args()

    audit_path = args.month_slice_dir / "sender-month-slices-audit.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    months = args.months or audit.get("months", [])
    if not months or len(set(months)) != len(months):
        raise SystemExit("months must be a non-empty unique list")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    rendered: dict[str, tuple[Path, str, list[dict]]] = {}
    for month in months:
        expected = audit.get("month_slices", {}).get(month)
        if not expected:
            raise SystemExit(f"month missing from audit: {month}")
        source = args.month_slice_dir / expected["output_path"]
        rows = read_and_validate(month, source, expected)
        destination = args.output_dir / f"{month}.md"
        content = render_month(month, rows, expected, expected["output_sha256"])
        rendered[month] = (destination, content, rows)

    index_path = args.output_dir / "README.md"
    targets = [destination for destination, _, _ in rendered.values()] + [index_path]
    existing = [path for path in targets if path.exists()]
    if existing:
        raise SystemExit("refusing to overwrite existing output(s): " + ", ".join(map(str, existing)))

    lines = [
        "# 지비톡 받은 쪽지 월별 보관",
        "",
        "본문은 날짜·행 지문·본문 해시를 확인한 JSONL에서 생성했습니다. 발신자가 확인되지 않은 항목은 명시적으로 표시했습니다. 이 캡처가 앱 받은쪽지함의 전체 기록인지는 검증되지 않았습니다.",
        "",
        "| 월 | 건수 | 발신자 확인 | 발신자 미확인 | 파일 |",
        "|---|---:|---:|---:|---|",
    ]
    for month in months:
        summary = audit["month_slices"][month]
        lines.append(
            f"| {month} | {summary['record_count']} | {summary['sender_count']} | "
            f"{summary['missing_sender_count']} | [{month}.md]({month}.md) |"
        )
    lines.extend([
        "",
        "발신자 미확인 항목은 화면 검증 전까지 이름을 추정하지 않습니다. 같은 날짜의 수신 시각은 확보되지 않았으므로 날짜 안의 엄밀한 시간 순서는 보증하지 않습니다.",
        "",
    ])
    index_content = "\n".join(lines)

    for destination, content, _ in rendered.values():
        with destination.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
    with index_path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(index_content)

    result = {
        "output_dir": str(args.output_dir.resolve()),
        "files": {
            str(destination.name): {
                "record_count": len(rows),
                "sha256": sha256(content.encode("utf-8")),
            }
            for destination, content, rows in rendered.values()
        },
        "index": {"name": index_path.name, "sha256": sha256(index_content.encode("utf-8"))},
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
