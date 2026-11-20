"""NotebookLM MCP analyzer — calls NotebookLM, parses response tables.

Workflow:
  1. Reads merged bundles from md_merger output
  2. Sends analysis prompts to NotebookLM via MCP
  3. Parses markdown table responses
  4. Validates against v13 schema
  5. Outputs CSV compatible with apply_gemini_recommendations.py

Usage:
  # Analyze with NotebookLM (interactive — needs notebook URL or ID)
  python notebooklm_analyzer.py --notebook-url <URL> --tier full

  # Parse an already-saved NotebookLM response
  python notebooklm_analyzer.py --parse-file response.md --output recommendations.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from notebooklm_prompts import (
    PROMPT_FULL,
    PROMPT_LINKS,
    PROMPT_TITLE,
    select_prompt,
    validate_row,
)


# ── 응답 파서 ─────────────────────────────────────

@dataclass
class ParsedRow:
    """Single parsed recommendation row."""
    raw: dict[str, str]
    issues: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.issues) == 0

    @property
    def source_path(self) -> str:
        return self.raw.get("source_path", "")


def _normalize_cell(value: str) -> str:
    """Clean table cell."""
    v = str(value or "").strip().strip("\ufeff").strip("`")
    return v


def _detect_columns(header_line: str) -> list[str]:
    """Detect column names from a markdown table header."""
    cells = [_normalize_cell(c) for c in header_line.split("|")]
    # Filter empty cells from leading/trailing pipes
    return [c for c in cells if c]


def _is_separator_line(line: str) -> bool:
    """Check if line is a markdown table separator (---|---|---)."""
    stripped = line.strip().strip("|")
    parts = stripped.split("|")
    return all(re.match(r"^[\s:-]+$", p) for p in parts if p.strip())


def parse_markdown_table(text: str) -> list[dict[str, str]]:
    """Parse markdown pipe-delimited tables from NotebookLM response.

    Handles:
      - Multiple tables in one response
      - Tables with or without leading/trailing pipes
      - Separator lines (---|--- )
      - Extra whitespace, code fences
    """
    lines = text.splitlines()
    rows: list[dict[str, str]] = []
    headers: list[str] = []
    in_table = False

    for line in lines:
        stripped = line.strip()

        # Skip empty, code fences
        if not stripped or stripped.startswith("```"):
            in_table = False
            headers = []
            continue

        # Detect header line
        if "|" in stripped and not in_table:
            candidate_headers = _detect_columns(stripped)
            if len(candidate_headers) >= 3 and "source_path" in candidate_headers:
                headers = candidate_headers
                in_table = True
                continue

            # Also check for Korean header variants
            has_key_headers = any(
                k in stripped for k in ("source_path", "현재 제목", "bundle_file")
            )
            if has_key_headers and len(candidate_headers) >= 3:
                headers = candidate_headers
                in_table = True
                continue

        if in_table and _is_separator_line(stripped):
            continue

        if in_table and "|" in stripped and headers:
            cells = [_normalize_cell(c) for c in stripped.split("|")]
            cells = [c for c in cells if c is not None]  # keep empties
            # Remove leading/trailing empty from pipe format
            if stripped.startswith("|"):
                # Split produces empty first element
                raw_split = stripped.split("|")
                cells = [_normalize_cell(c) for c in raw_split[1:]]
                if stripped.endswith("|") and cells:
                    cells = cells[:-1]

            # Pad if fewer cells than headers
            while len(cells) < len(headers):
                cells.append("")

            row = {}
            for i, header in enumerate(headers):
                row[header] = cells[i] if i < len(cells) else ""
            rows.append(row)
        elif in_table:
            # Non-table line encountered, end table
            in_table = False
            headers = []

    return rows


def parse_and_validate(text: str) -> list[ParsedRow]:
    """Parse response text and validate each row."""
    raw_rows = parse_markdown_table(text)
    results: list[ParsedRow] = []

    for raw in raw_rows:
        issues = validate_row(raw)
        results.append(ParsedRow(raw=raw, issues=issues))

    return results


# ── CSV 출력 ──────────────────────────────────────

FULL_COLUMNS = [
    "bundle_file",
    "source_path",
    "현재 제목",
    "제안 제목",
    "domain",
    "engine",
    "topic",
    "type",
    "연결 후보",
    "처리 제안",
    "확신도",
    "이유",
]

TITLE_COLUMNS = [
    "bundle_file",
    "source_path",
    "현재 제목",
    "제안 제목",
    "유지 가능 여부",
    "이유",
]

LINKS_COLUMNS = [
    "bundle_file",
    "source_path",
    "현재 제목",
    "연결 후보",
    "연결 종류",
    "이유",
    "처리 제안",
    "확신도",
]


def _columns_for_tier(tier: str) -> list[str]:
    """Return column list for the given tier."""
    return {
        "full": FULL_COLUMNS,
        "title": TITLE_COLUMNS,
        "links": LINKS_COLUMNS,
    }.get(tier, FULL_COLUMNS)


def write_csv(rows: list[ParsedRow], output_path: Path, tier: str) -> int:
    """Write validated rows to CSV. Returns count of rows written."""
    columns = _columns_for_tier(tier)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    written = 0
    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for parsed in rows:
            if parsed.source_path:  # skip rows without source_path
                writer.writerow(parsed.raw)
                written += 1

    return written


def write_validation_report(
    rows: list[ParsedRow], report_path: Path
) -> tuple[int, int]:
    """Write validation report. Returns (valid_count, issue_count)."""
    report_path.parent.mkdir(parents=True, exist_ok=True)

    valid_count = sum(1 for r in rows if r.is_valid)
    issue_count = sum(1 for r in rows if not r.is_valid)

    lines = [
        "# NotebookLM 분석 검증 리포트",
        "",
        f"- 검증 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 총 행: {len(rows)}",
        f"- 통과: {valid_count}",
        f"- 문제: {issue_count}",
        "",
    ]

    if issue_count > 0:
        lines.append("## 문제 항목")
        lines.append("")
        lines.append("| source_path | 문제 |")
        lines.append("|---|---|")
        for parsed in rows:
            if not parsed.is_valid:
                sp = parsed.source_path or "(없음)"
                for issue in parsed.issues:
                    lines.append(f"| `{sp}` | {issue} |")
        lines.append("")

    lines.append("## 통과 항목")
    lines.append("")
    lines.append("| source_path | 처리 제안 | 확신도 |")
    lines.append("|---|---|---|")
    for parsed in rows:
        if parsed.is_valid:
            sp = parsed.source_path
            action = parsed.raw.get("처리 제안", "")
            conf = parsed.raw.get("확신도", "")
            lines.append(f"| `{sp}` | {action} | {conf} |")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return valid_count, issue_count


# ── NotebookLM MCP 호출 (스텁 — 실제 MCP 연동) ──────

def call_notebooklm_mcp(
    question: str,
    notebook_url: str | None = None,
    notebook_id: str | None = None,
    session_id: str | None = None,
) -> dict:
    """Call NotebookLM via MCP server.

    This function will be called by the orchestrator.
    In practice, this delegates to mcp_notebooklm_ask_question.

    Returns dict with: answer, session_id, status
    """
    # This is a structural stub.
    # In actual use, this will be called from orchestrator.py
    # which has access to MCP tools (via Antigravity/Claude).
    raise NotImplementedError(
        "NotebookLM MCP 호출은 orchestrator.py에서 Antigravity 에이전트를 통해 실행됩니다.\n"
        "직접 실행하려면 --parse-file 옵션으로 이미 저장된 응답을 파싱하세요."
    )


# ── CLI ───────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="NotebookLM 분석 및 추천 CSV 생성",
    )
    sub = parser.add_subparsers(dest="command")

    # 1. parse — 이미 저장된 NotebookLM 응답 파싱
    p_parse = sub.add_parser("parse", help="저장된 NotebookLM 응답 파일 파싱")
    p_parse.add_argument("response_file", help="NotebookLM 응답 텍스트/마크다운 파일")
    p_parse.add_argument(
        "--output", "-o", default=None, help="출력 CSV 경로 (기본: 같은 폴더에 .csv)"
    )
    p_parse.add_argument(
        "--tier",
        choices=["full", "title", "links"],
        default="full",
        help="분석 티어 (기본: full)",
    )

    # 2. prompt — 프롬프트만 출력 (클립보드 복사용)
    p_prompt = sub.add_parser("prompt", help="분석 프롬프트 출력")
    p_prompt.add_argument(
        "--tier",
        choices=["full", "title", "links"],
        default="full",
        help="프롬프트 티어",
    )

    # 3. validate — CSV 파일 검증
    p_validate = sub.add_parser("validate", help="기존 CSV 검증")
    p_validate.add_argument("csv_file", help="검증할 CSV 파일")

    return parser


def cmd_parse(args: argparse.Namespace) -> int:
    """Parse a saved NotebookLM response file."""
    response_path = Path(args.response_file).resolve()
    if not response_path.exists():
        print(f"파일을 찾을 수 없습니다: {response_path}", file=sys.stderr)
        return 1

    text = response_path.read_text(encoding="utf-8")
    parsed = parse_and_validate(text)

    if not parsed:
        print("응답에서 테이블을 찾을 수 없습니다.", file=sys.stderr)
        return 1

    # Output CSV
    if args.output:
        csv_path = Path(args.output).resolve()
    else:
        csv_path = response_path.with_suffix(".csv")

    written = write_csv(parsed, csv_path, tier=args.tier)

    # Validation report
    report_path = csv_path.with_name(csv_path.stem + "_validation.md")
    valid, issues = write_validation_report(parsed, report_path)

    print(f"파싱 완료: {len(parsed)}행")
    print(f"CSV 출력: {csv_path} ({written}행)")
    print(f"검증 리포트: {report_path} (통과 {valid} / 문제 {issues})")
    return 0


def cmd_prompt(args: argparse.Namespace) -> int:
    """Print prompt for copy-paste to NotebookLM."""
    prompt = select_prompt(args.tier)
    print(prompt)
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate an existing CSV file."""
    csv_path = Path(args.csv_file).resolve()
    if not csv_path.exists():
        print(f"파일을 찾을 수 없습니다: {csv_path}", file=sys.stderr)
        return 1

    with csv_path.open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    parsed = [ParsedRow(raw=row, issues=validate_row(row)) for row in rows]

    report_path = csv_path.with_name(csv_path.stem + "_validation.md")
    valid, issues = write_validation_report(parsed, report_path)

    print(f"검증 완료: {len(parsed)}행 (통과 {valid} / 문제 {issues})")
    print(f"리포트: {report_path}")
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "parse":
        return cmd_parse(args)
    elif args.command == "prompt":
        return cmd_prompt(args)
    elif args.command == "validate":
        return cmd_validate(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
