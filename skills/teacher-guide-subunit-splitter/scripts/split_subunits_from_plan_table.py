#!/usr/bin/env python3
"""
Split a teacher-guide PDF into smaller PDFs.

The splitter now prefers front-matter topic lists or table-of-contents pages
and falls back to plan-table parsing when a usable TOC cannot be found.
"""

from __future__ import annotations

import argparse
import json
import re
import site
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

PLAN_TITLE_KEYWORDS = (
    "단원 지도 계획",
    "단원의 지도 계획",
    "주제별 지도 계획",
    "차시별 지도 계획",
    "연간 학습 지도 계획",
    "미술 시간 계획표",
    "학습 계획표",
    "지도 계획",
)
GUIDE_COLUMN_KEYWORDS = ("지", "지도서", "쪽")
HEADER_STOP_WORDS = {
    "영역",
    "차시",
    "쪽",
    "지",
    "지도서",
    "단원",
    "학습",
    "주제",
    "내용",
}
TOC_SECTION_HINTS = (
    "지도의 실제",
    "차례",
    "목차",
    "총론",
    "연간 학습 지도 계획",
    "교수",
)
OVERVIEW_TITLE_KEYWORDS = ("단원 개관", "단원의 개관", "제재 개관", "제재의 개관")
MAX_TITLE_LENGTH = 80
MAX_FILENAME_TITLE_LENGTH = 24
MAX_TOC_SCAN_PAGES = 24
MAX_AUTO_OFFSET = 12

GRADE_LINE_RE = re.compile(r"^\s*([1-6])\s*학년\s*$")
TRAILING_PAGE_RE = re.compile(r"^(?P<title>.+?)\s+(?P<page>\d{1,3})$")
OVERVIEW_PARENT_RE = re.compile(r"^\s*(\d{1,2})\.\s*(.+?)\s*$")
PLAN_RANGE_AT_END_RE = re.compile(r"(?P<range>\d{1,3}\s*[~-]\s*\d{1,3})\s*$")


@dataclass(frozen=True)
class TocEntry:
    title: str
    printed_page: int
    source_page: int
    context: tuple[str, ...]
    level: str


def ensure_user_site_on_path() -> None:
    try:
        user_site = site.getusersitepackages()
    except Exception:
        return

    if user_site and user_site not in sys.path:
        sys.path.append(user_site)


ensure_user_site_on_path()


def normalize_space(text: str | None) -> str:
    return " ".join((text or "").split())


def sanitize_filename_part(value: str) -> str:
    cleaned = normalize_space(value)
    cleaned = re.sub(r'[<>:"/\\|?*]', "_", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ._")
    return cleaned


def shorten_title(value: str, *, max_chars: int = MAX_TITLE_LENGTH) -> str:
    text = normalize_space(value)
    if len(text) <= max_chars:
        return text

    first_sentence = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)[0]
    if len(first_sentence) <= max_chars:
        return first_sentence

    words = first_sentence.split()
    shortened = " ".join(words[:10]).strip()
    if len(shortened) > max_chars:
        shortened = shortened[:max_chars].rstrip()
    return f"{shortened}..."


def build_output_filename(index: int, title: str, start_page: int, end_page: int) -> str:
    title_part = sanitize_filename_part(shorten_title(title, max_chars=MAX_FILENAME_TITLE_LENGTH))
    page_part = f"p{start_page}-{end_page}"
    if title_part:
        return f"subunit_{index:02d}_{title_part}_{page_part}.pdf"
    return f"subunit_{index:02d}_{page_part}.pdf"


def build_run_directory_name(pdf_path: str | Path) -> str:
    return sanitize_filename_part(Path(pdf_path).stem)[:50] or "teacher_guide"


def parse_page_ranges(cell_text: str | None) -> list[tuple[int, int]]:
    text = normalize_space(cell_text)
    if not text:
        return []

    ranges: list[tuple[int, int]] = []
    for start, end in re.findall(r"(\d{1,3})\s*[-~]\s*(\d{1,3})", text):
        s = int(start)
        e = int(end)
        if e < s:
            s, e = e, s
        ranges.append((s, e))

    if ranges:
        return ranges

    numbers = [int(x) for x in re.findall(r"\b\d{1,3}\b", text)]
    if not numbers:
        return []
    return [(min(numbers), max(numbers))]


def extract_pdf_range(
    pdf_path: Path,
    start_page_1based: int,
    end_page_1based: int,
    output_path: Path,
) -> Path:
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError as exc:
        raise RuntimeError("pypdf is required. Run `pip install pypdf`.") from exc

    reader = PdfReader(str(pdf_path))
    total_pages = len(reader.pages)

    start = max(1, int(start_page_1based))
    end = min(total_pages, int(end_page_1based))
    if end < start:
        start, end = end, start

    writer = PdfWriter()
    for page_index in range(start - 1, end):
        writer.add_page(reader.pages[page_index])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as file_obj:
        writer.write(file_obj)
    return output_path


def load_pdfplumber():
    try:
        import pdfplumber
    except ImportError as exc:
        raise RuntimeError("pdfplumber is required. Run `pip install pdfplumber`.") from exc
    return pdfplumber


def extract_page_text(page) -> str:
    try:
        return page.extract_text() or ""
    except Exception:
        return ""


def normalize_toc_title(title: str) -> str:
    cleaned = normalize_space(title)
    cleaned = cleaned.strip("-.·•: ")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def halve_duplicate_runs(text: str) -> str:
    if not text:
        return text

    parts: list[str] = []
    index = 0
    while index < len(text):
        next_index = index + 1
        while next_index < len(text) and text[next_index] == text[index]:
            next_index += 1
        run_length = next_index - index
        if run_length >= 2 and run_length % 2 == 0:
            parts.append(text[index] * (run_length // 2))
        else:
            parts.append(text[index] * run_length)
        index = next_index
    return "".join(parts)


def canonicalize_plan_header_line(line: str) -> str:
    replacements = {
        "차차시시명명": "차시명",
        "차차시시": "차시",
        "주주요요 학학습습 내내용용": "주요 학습 내용",
        "학학생생 활활동동": "학생 활동",
        "쪽쪽수수": "쪽수",
        "단단원원": "단원",
    }
    canonical = line
    for source, target in replacements.items():
        canonical = canonical.replace(source, target)
    return normalize_space(halve_duplicate_runs(canonical))


def is_probably_toc_title(title: str) -> bool:
    if not title:
        return False
    if len(title) < 2 or len(title) > 60:
        return False
    if re.search(r"\d{1,3}\s*[-~]\s*\d{1,3}", title):
        return False
    if title.count(" ") > 10:
        return False
    if sum(char.isdigit() for char in title) > 4:
        return False
    return True


def classify_toc_entry(title: str, context: tuple[str, ...]) -> str:
    if "계획표" in title:
        return "plan"
    if re.match(r"^\d{1,2}\s", title):
        return "subunit"
    if title.startswith("프로젝트"):
        return "project"
    if any("학년" in part for part in context):
        return "subunit"
    return "section"


def extract_toc_entries_from_text(text: str, source_page: int) -> list[TocEntry]:
    entries: list[TocEntry] = []
    current_section: str | None = None
    current_grade: str | None = None

    for raw_line in text.splitlines():
        line = normalize_space(raw_line.replace("•", " ").replace("·", " "))
        if not line:
            continue

        grade_match = GRADE_LINE_RE.match(line)
        if grade_match:
            current_grade = f"{grade_match.group(1)}학년"
            continue

        match = TRAILING_PAGE_RE.match(line)
        if match:
            title = normalize_toc_title(match.group("title"))
            if not is_probably_toc_title(title):
                continue

            context = tuple(part for part in (current_section, current_grade) if part)
            entries.append(
                TocEntry(
                    title=title,
                    printed_page=int(match.group("page")),
                    source_page=source_page,
                    context=context,
                    level=classify_toc_entry(title, context),
                )
            )
            continue

        if len(line) <= 24 and any(hint in line for hint in TOC_SECTION_HINTS):
            current_section = line

    return entries


def score_toc_page(page_text: str, entries: list[TocEntry]) -> int:
    if len(entries) < 3:
        return -1

    pages = [entry.printed_page for entry in entries]
    ascending_pairs = sum(1 for left, right in zip(pages, pages[1:]) if right > left)
    short_titles = sum(1 for entry in entries if len(entry.title) <= 24)

    score = len(entries) * 4
    score += ascending_pairs
    score += short_titles

    lowered = page_text.lower()
    if "차례" in lowered or "목차" in lowered:
        score += 4
    if "계획표" in page_text:
        score += 6
    if any(any("학년" in ctx for ctx in entry.context) for entry in entries):
        score += 5

    return score


def dedupe_toc_entries(entries: list[TocEntry]) -> list[TocEntry]:
    seen: set[tuple[str, int, tuple[str, ...]]] = set()
    result: list[TocEntry] = []

    for entry in entries:
        key = (entry.title, entry.printed_page, entry.context)
        if key in seen:
            continue
        seen.add(key)
        result.append(entry)

    result.sort(key=lambda item: (item.printed_page, item.source_page, item.title))
    return result


def find_toc_entries(pdf_doc, scan_pages: int) -> list[TocEntry]:
    limit = min(scan_pages, len(pdf_doc.pages), MAX_TOC_SCAN_PAGES)
    candidates: list[TocEntry] = []

    for page_index in range(limit):
        text = extract_page_text(pdf_doc.pages[page_index])
        entries = extract_toc_entries_from_text(text, source_page=page_index + 1)
        if score_toc_page(text, entries) >= 18:
            candidates.extend(entries)

    return dedupe_toc_entries(candidates)


def entry_search_tokens(title: str) -> list[str]:
    title = re.sub(r"^\d{1,2}\s*", "", normalize_space(title))
    tokens = [token for token in re.findall(r"[0-9A-Za-z가-힣]+", title) if len(token) >= 2]
    tokens.sort(key=len, reverse=True)
    return tokens[:3]


def entry_matches_page(pdf_doc, page_number: int, tokens: list[str]) -> bool:
    if page_number < 1 or page_number > len(pdf_doc.pages) or not tokens:
        return False

    for probe in (page_number - 1, page_number, page_number + 1):
        if probe < 1 or probe > len(pdf_doc.pages):
            continue
        text = normalize_space(extract_page_text(pdf_doc.pages[probe - 1]))
        if not text:
            continue
        if all(token in text for token in tokens[:2]) or any(token in text for token in tokens):
            return True
    return False


def count_valid_entries(entries: list[TocEntry], offset: int, total_pages: int) -> int:
    return sum(1 for entry in entries if 1 <= entry.printed_page + offset <= total_pages)


def score_offset(pdf_doc, entries: list[TocEntry], offset: int) -> int:
    total_pages = len(pdf_doc.pages)
    valid_entries = [entry for entry in entries if 1 <= entry.printed_page + offset <= total_pages]
    if not valid_entries:
        return -10_000

    score = len(valid_entries) * 5
    score -= abs(offset)

    mapped_pages = [entry.printed_page + offset for entry in valid_entries]
    score += sum(1 for left, right in zip(mapped_pages, mapped_pages[1:]) if right > left)

    anchor_entries = [entry for entry in valid_entries if entry.level in {"subunit", "project"}][:6]
    for entry in anchor_entries:
        if entry_matches_page(pdf_doc, entry.printed_page + offset, entry_search_tokens(entry.title)):
            score += 8

    return score


def infer_toc_page_offset(pdf_doc, entries: list[TocEntry]) -> int:
    total_pages = len(pdf_doc.pages)
    if not entries:
        return 0

    zero_valid = count_valid_entries(entries, 0, total_pages)
    if zero_valid >= max(3, len(entries) // 2):
        candidate_offsets = [0] + [offset for offset in range(-MAX_AUTO_OFFSET, MAX_AUTO_OFFSET + 1) if offset != 0]
    else:
        candidate_offsets = list(range(-MAX_AUTO_OFFSET, MAX_AUTO_OFFSET + 1))

    best_offset = 0
    best_score = -10_000
    for offset in candidate_offsets:
        offset_score = score_offset(pdf_doc, entries, offset)
        if offset_score > best_score:
            best_score = offset_score
            best_offset = offset

    return best_offset


def context_to_section_title(context: tuple[str, ...]) -> str | None:
    grade = next((part for part in context if "학년" in part), None)
    section = next((part for part in context if "지도의 실제" in part or "총론" in part), None)

    if grade and section and "지도의 실제" in section:
        return f"{grade} 지도의 실제"
    if section:
        return section
    if grade:
        return grade
    return None


def detect_leading_section_title(pdf_doc, first_entry_page: int) -> str:
    scan_limit = min(first_entry_page - 1, 15, len(pdf_doc.pages))
    combined = " ".join(extract_page_text(pdf_doc.pages[index]) for index in range(scan_limit))
    if "총론" in combined:
        return "총론"
    if "머리말" in combined or "편찬 방향" in combined:
        return "총론"
    return "앞부분"


def build_sections_from_toc_entries(valid_entries: list[dict], total_pages: int) -> list[dict]:
    sections: list[dict] = []
    seen_titles: list[tuple[str, int]] = []

    for entry in valid_entries:
        section_title = context_to_section_title(tuple(entry["context"]))
        if not section_title:
            continue
        if seen_titles and seen_titles[-1][0] == section_title:
            continue
        seen_titles.append((section_title, entry["start_page"]))

    for index, (title, start_page) in enumerate(seen_titles, start=1):
        next_start = seen_titles[index][1] if index < len(seen_titles) else total_pages + 1
        sections.append(
            {
                "index": index,
                "title": title,
                "start_page": start_page,
                "end_page": max(start_page, next_start - 1),
            }
        )

    return sections


def clone_group(group: dict) -> dict:
    cloned = dict(group)
    cloned["context"] = list(group.get("context", []))
    cloned["page_ranges_raw"] = list(group.get("page_ranges_raw", []))
    return cloned


def renumber_groups(groups: list[dict]) -> list[dict]:
    for index, group in enumerate(groups, start=1):
        group["index"] = index
    return groups


def build_groups_from_toc_entries(pdf_doc, entries: list[TocEntry], page_offset: int) -> tuple[list[dict], list[dict], int]:
    if not entries:
        return [], [], 0

    auto_offset = infer_toc_page_offset(pdf_doc, entries)
    effective_offset = auto_offset + page_offset
    total_pages = len(pdf_doc.pages)

    valid_entries: list[dict] = []
    for entry in entries:
        mapped_page = entry.printed_page + effective_offset
        if not 1 <= mapped_page <= total_pages:
            continue
        valid_entries.append(
            {
                "title": entry.title,
                "source_title": entry.title,
                "start_page": mapped_page,
                "context": list(entry.context),
                "level": entry.level,
                "source_page": entry.source_page,
                "printed_page": entry.printed_page,
            }
        )

    valid_entries.sort(key=lambda item: (item["start_page"], item["source_page"], item["title"]))
    deduped_valid_entries: list[dict] = []
    seen_starts: set[tuple[str, int]] = set()
    for entry in valid_entries:
        key = (entry["title"], entry["start_page"])
        if key in seen_starts:
            continue
        seen_starts.add(key)
        deduped_valid_entries.append(entry)
    valid_entries = deduped_valid_entries

    if len(valid_entries) < 3:
        return [], [], auto_offset

    preferred_entries = [
        entry
        for entry in valid_entries
        if entry["level"] in {"plan", "subunit", "project"} or any("학년" in ctx for ctx in entry["context"])
    ]
    leaf_entries = preferred_entries if len(preferred_entries) >= 3 else valid_entries

    groups: list[dict] = []
    first_start = leaf_entries[0]["start_page"]
    if first_start > 1:
        leading_title = detect_leading_section_title(pdf_doc, first_start)
        groups.append(
            {
                "index": 1,
                "title": leading_title,
                "source_title": leading_title,
                "start_page": 1,
                "end_page": first_start - 1,
                "row_evidence": 1,
                "page_ranges_raw": [(1, first_start - 1)],
                "method": "toc_leading_section",
                "context": [],
                "detected_level": "section",
            }
        )

    start_index = len(groups) + 1
    for offset_index, entry in enumerate(leaf_entries, start=start_index):
        next_start = (
            leaf_entries[offset_index - start_index + 1]["start_page"]
            if offset_index - start_index + 1 < len(leaf_entries)
            else total_pages + 1
        )
        end_page = max(entry["start_page"], next_start - 1)
        groups.append(
            {
                "index": offset_index,
                "title": shorten_title(entry["title"]),
                "source_title": entry["source_title"],
                "start_page": entry["start_page"],
                "end_page": end_page,
                "row_evidence": 1,
                "page_ranges_raw": [(entry["printed_page"], entry["printed_page"])],
                "method": "toc",
                "context": entry["context"],
                "detected_level": entry["level"],
            }
        )

    section_source_entries = preferred_entries if preferred_entries else valid_entries
    sections = build_sections_from_toc_entries(section_source_entries, total_pages)
    if groups and groups[0]["title"] in {"총론", "앞부분"} and groups[0]["start_page"] == 1:
        sections.insert(
            0,
            {
                "index": 1,
                "title": groups[0]["title"],
                "start_page": groups[0]["start_page"],
                "end_page": groups[0]["end_page"],
            },
        )
        for index, section in enumerate(sections, start=1):
            section["index"] = index

    return groups, sections, auto_offset


def score_table_for_plan(table: list[list[str | None]]) -> int:
    if not table:
        return -1

    flattened: list[str] = []
    page_range_hits = 0
    long_cell_penalty = 0
    probable_title_rows = 0

    for row in table:
        row_first = normalize_space(row[0] if row else "")
        if is_probably_group_title(row_first):
            probable_title_rows += 1

        for cell in row:
            cell_text = normalize_space(cell)
            if not cell_text:
                continue
            flattened.append(cell_text)
            page_range_hits += len(parse_page_ranges(cell_text))
            if len(cell_text) > 80:
                long_cell_penalty += 1

    if not flattened:
        return -1

    combined = " ".join(flattened).lower()
    title_hits = sum(4 for keyword in PLAN_TITLE_KEYWORDS if keyword in combined)
    guide_hits = sum(2 for keyword in GUIDE_COLUMN_KEYWORDS if keyword in combined)
    return title_hits + guide_hits + page_range_hits * 2 + probable_title_rows - long_cell_penalty * 3


def detect_guide_column(table: list[list[str | None]]) -> int | None:
    if not table:
        return None

    max_columns = max((len(row) for row in table), default=0)
    if max_columns == 0:
        return None

    column_scores: dict[int, int] = defaultdict(int)
    for row in table[:12]:
        for index, raw_cell in enumerate(row):
            cell = normalize_space(raw_cell)
            if not cell:
                continue
            if cell in GUIDE_COLUMN_KEYWORDS:
                column_scores[index] += 4
            elif any(keyword in cell for keyword in GUIDE_COLUMN_KEYWORDS):
                column_scores[index] += 2
            if parse_page_ranges(cell):
                column_scores[index] += 2

    if not column_scores:
        return None
    return max(column_scores.items(), key=lambda item: item[1])[0]


def find_plan_table_pages(pdf_doc, scan_pages: int, title_keywords: Iterable[str]) -> list[int]:
    total_pages = len(pdf_doc.pages)
    scan_limit = min(scan_pages, total_pages)
    keywords = [keyword.lower() for keyword in title_keywords]

    matches: list[int] = []
    for page_index in range(scan_limit):
        text = extract_page_text(pdf_doc.pages[page_index]).lower()
        if any(keyword in text for keyword in keywords):
            matches.append(page_index)

    return matches


def extract_tables_from_page(page) -> list[list[list[str | None]]]:
    tables: list[list[list[str | None]]] = []

    try:
        for table in page.find_tables()[:5]:
            extracted = table.extract()
            if extracted:
                tables.append(extracted)
    except Exception:
        pass

    if tables:
        return tables

    try:
        for table in (page.extract_tables() or [])[:5]:
            if table:
                tables.append(table)
    except Exception:
        pass

    return tables


def is_header_cell(cell_text: str) -> bool:
    return normalize_space(cell_text) in HEADER_STOP_WORDS


def is_probably_group_title(text: str) -> bool:
    normalized = normalize_space(text)
    if not normalized:
        return False
    if len(normalized) > 40:
        return False
    if parse_page_ranges(normalized):
        return False
    if normalized.count(".") > 1:
        return False
    return True


def pick_row_title(row: list[str | None], guide_column: int) -> str | None:
    limit = min(guide_column, len(row))
    for index in range(limit):
        candidate = normalize_space(row[index])
        if is_header_cell(candidate):
            continue
        if is_probably_group_title(candidate):
            return candidate
    return None


def build_groups_from_tables(
    tables: list[list[list[str | None]]],
    guide_column_override: int | None,
) -> list[dict]:
    groups: dict[str, dict] = {}
    current_group_title: str | None = None

    for table in tables:
        if not table:
            continue

        guide_column = guide_column_override
        if guide_column is None:
            guide_column = detect_guide_column(table)
        if guide_column is None:
            guide_column = max((len(row) for row in table if row), default=0) - 1
            if guide_column < 0:
                continue

        for row in table:
            if not row:
                continue

            row_title = pick_row_title(row, guide_column)
            guide_cell = normalize_space(row[guide_column] if len(row) > guide_column else "")

            if row_title:
                current_group_title = row_title
            if not current_group_title or not guide_cell:
                continue

            page_ranges = parse_page_ranges(guide_cell)
            if not page_ranges:
                continue

            group = groups.setdefault(
                current_group_title,
                {
                    "title": current_group_title,
                    "page_ranges": [],
                    "row_evidence": 0,
                },
            )
            group["page_ranges"].extend(page_ranges)
            group["row_evidence"] += 1

    final_groups: list[dict] = []
    for group in groups.values():
        starts = [start for start, _ in group["page_ranges"]]
        ends = [end for _, end in group["page_ranges"]]
        if not starts or not ends:
            continue
        final_groups.append(
            {
                "title": group["title"],
                "start_page": min(starts),
                "end_page": max(ends),
                "row_evidence": group["row_evidence"],
                "page_ranges": group["page_ranges"],
                "method": "plan_table",
            }
        )

    final_groups.sort(key=lambda item: (item["start_page"], item["title"]))
    return final_groups


def build_groups_from_plan_tables(pdf_doc, scan_pages: int, page_offset: int, z_col: int | None) -> tuple[list[dict], int]:
    candidate_pages = find_plan_table_pages(pdf_doc, scan_pages=scan_pages, title_keywords=PLAN_TITLE_KEYWORDS)
    if not candidate_pages:
        candidate_pages = find_plan_table_pages(
            pdf_doc,
            scan_pages=len(pdf_doc.pages),
            title_keywords=PLAN_TITLE_KEYWORDS,
        )
    if not candidate_pages:
        return [], 0

    extracted_tables: list[list[list[str | None]]] = []
    for page_index in candidate_pages:
        extracted_tables.extend(extract_tables_from_page(pdf_doc.pages[page_index]))
    if not extracted_tables:
        return [], 0

    scored_tables = sorted(
        ((score_table_for_plan(table), table) for table in extracted_tables),
        key=lambda item: item[0],
        reverse=True,
    )
    top_tables = [table for score, table in scored_tables if score > 0][:5]
    parsed_groups = build_groups_from_tables(top_tables, guide_column_override=z_col)
    if not parsed_groups:
        return [], 0

    final_groups: list[dict] = []
    for index, group in enumerate(parsed_groups, start=1):
        start_page = group["start_page"] + page_offset
        end_page = group["end_page"] + page_offset
        if end_page < start_page:
            start_page, end_page = end_page, start_page

        final_groups.append(
            {
                "index": index,
                "title": shorten_title(group["title"]),
                "source_title": group["title"],
                "start_page": start_page,
                "end_page": end_page,
                "row_evidence": group["row_evidence"],
                "page_ranges_raw": group["page_ranges"],
                "method": group["method"],
                "context": [],
                "detected_level": "detail",
            }
        )

    return final_groups, 0


def looks_like_plan_text_header(line: str) -> bool:
    canonical = canonicalize_plan_header_line(line)
    return "차시명" in canonical and "쪽수" in canonical


def is_plan_text_candidate_page(lines: list[str]) -> bool:
    preview = lines[:8]
    if any(any(keyword in line for keyword in PLAN_TITLE_KEYWORDS) for line in preview):
        return True
    return any(looks_like_plan_text_header(line) for line in preview)


def normalize_plan_row_token(token: str) -> str:
    normalized = halve_duplicate_runs(token.replace("∼", "~"))
    normalized = normalized.replace("~~", "~")
    normalized = normalized.replace("--", "-")
    return normalized


def is_plan_row_token(token: str) -> bool:
    normalized = normalize_plan_row_token(token)
    return bool(re.fullmatch(r"\d{1,2}(?:[~-]\d{1,2})?", normalized))


def rough_row_title(rest: str) -> str:
    text = normalize_space(PLAN_RANGE_AT_END_RE.sub("", rest))
    text = text.split("[", 1)[0].strip()

    repeated = collapse_leading_repeated_words(text)
    if repeated:
        text = repeated

    endings = (
        "알아볼까요",
        "살펴볼까요",
        "이야기해 볼까요",
        "표현해 볼까요",
        "이야기해 볼까요",
        "찾아볼까요",
        "무엇일까요",
        "볼까요",
        "확인해요",
        "완성해요",
        "함께해요",
        "확인해요",
        "펼쳐요",
    )
    for ending in endings:
        if ending in text:
            return text.split(ending, 1)[0].strip() + ending

    if "단원 도입" in text:
        return "단원 도입"
    if "생각을 펼쳐요" in text:
        return "생각을 펼쳐요"
    if "재미있게 확인해요" in text:
        return "재미있게 확인해요"
    if "생각 그물을 완성해요" in text:
        return "생각 그물을 완성해요"

    if len(text) <= 36:
        return text

    return text[:36].strip()


def collapse_leading_repeated_words(text: str) -> str:
    words = text.split()
    if len(words) < 4:
        return text

    max_block = min(6, len(words) // 2)
    for size in range(max_block, 1, -1):
        if words[:size] == words[size : size * 2]:
            return " ".join(words[size:])
    return text


def is_valid_plan_text_row(row: dict) -> bool:
    title = normalize_space(row["title"])
    if not title:
        return False
    if re.match(r"^\d", title):
        return False
    if re.search(r"\s\d{1,3}$", title):
        return False
    if "작업자 확인자" in title:
        return False
    if "최종" in title and ".indd" in title:
        return False
    return True


def is_probably_footer_or_noise(line: str) -> bool:
    text = normalize_space(line)
    if not text:
        return True
    if "최종" in text and ".indd" in text:
        return True
    if re.search(r"\d{4}-\d{2}-\d{2}", text):
        return True
    if re.fullmatch(r"[\d\s~\-]+", text):
        return True
    return False


def extract_display_title_from_start_page(pdf_doc, start_page: int, fallback: str) -> str:
    if start_page < 1 or start_page > len(pdf_doc.pages):
        return shorten_title(fallback)

    text = extract_page_text(pdf_doc.pages[start_page - 1])
    lines = [normalize_space(line) for line in text.splitlines() if normalize_space(line)]
    for line in lines[:12]:
        if is_probably_footer_or_noise(line):
            continue
        if any(keyword in line for keyword in OVERVIEW_TITLE_KEYWORDS):
            continue
        if any(keyword in line for keyword in PLAN_TITLE_KEYWORDS):
            continue
        if line in {"학습 안내", "활동 안내", "차시", "교과서", "쪽"}:
            continue
        return shorten_title(line)
    return shorten_title(fallback)


def extract_plan_rows_from_text_pages(pdf_doc, scan_pages: int) -> list[dict]:
    total_pages = len(pdf_doc.pages)
    scan_limit = min(scan_pages, total_pages)
    rows: list[dict] = []

    for page_index in range(scan_limit):
        text = extract_page_text(pdf_doc.pages[page_index])
        if not text:
            continue
        lines = [normalize_space(line) for line in text.splitlines() if normalize_space(line)]
        if not lines or not is_plan_text_candidate_page(lines):
            continue

        header_found = False
        previous_lines: list[str] = []
        current_section = ""
        pending_title: str | None = None
        pending_ranges: list[tuple[int, int]] = []

        def finalize_pending() -> None:
            nonlocal pending_title, pending_ranges
            if not pending_title or not pending_ranges:
                pending_title = None
                pending_ranges = []
                return
            selected_range = max(pending_ranges, key=lambda item: (item[0], item[1]))
            rows.append(
                {
                    "title": pending_title,
                    "printed_start": selected_range[0],
                    "printed_end": selected_range[1],
                    "context": current_section,
                    "source_page": page_index + 1,
                }
            )
            pending_title = None
            pending_ranges = []

        for line in lines:
            if looks_like_plan_text_header(line):
                header_found = True
                for previous in reversed(previous_lines):
                    candidate = canonicalize_plan_header_line(previous)
                    if any(keyword in candidate for keyword in PLAN_TITLE_KEYWORDS):
                        continue
                    if len(candidate) <= 60:
                        current_section = candidate
                        break
                continue

            if not header_found:
                previous_lines.append(line)
                continue

            split = line.split(maxsplit=1)
            token = split[0]
            rest = split[1] if len(split) > 1 else ""
            if is_plan_row_token(token) and rest:
                finalize_pending()
                pending_title = rough_row_title(rest) or normalize_plan_row_token(token)
                pending_ranges = parse_page_ranges(rest)
                continue

            if pending_title:
                pending_ranges.extend(parse_page_ranges(line))

        finalize_pending()

    filtered_rows = [row for row in rows if is_valid_plan_text_row(row)]

    deduped: list[dict] = []
    seen: set[tuple[str, int, int]] = set()
    for row in filtered_rows:
        key = (row["title"], row["printed_start"], row["printed_end"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)

    deduped.sort(key=lambda item: (item["printed_start"], item["printed_end"], item["source_page"]))
    return deduped


def build_groups_from_plan_text(
    pdf_doc,
    scan_pages: int,
    page_offset: int,
    preferred_first_start: int | None = None,
) -> tuple[list[dict], int]:
    rows = extract_plan_rows_from_text_pages(pdf_doc, scan_pages=scan_pages)
    if not rows:
        return [], 0

    entries = [
        TocEntry(
            title=row["title"],
            printed_page=row["printed_start"],
            source_page=row["source_page"],
            context=(row["context"],) if row["context"] else (),
            level="subunit",
        )
        for row in rows
    ]
    if preferred_first_start is not None:
        auto_offset = preferred_first_start - rows[0]["printed_start"]
    else:
        auto_offset = infer_toc_page_offset(pdf_doc, entries)
    effective_offset = auto_offset + page_offset
    total_pages = len(pdf_doc.pages)

    groups: list[dict] = []
    for index, row in enumerate(rows, start=1):
        start_page = row["printed_start"] + effective_offset
        end_page = row["printed_end"] + effective_offset
        if not (1 <= start_page <= total_pages):
            continue
        if not (1 <= end_page <= total_pages):
            end_page = max(1, min(total_pages, end_page))
        if end_page < start_page:
            start_page, end_page = end_page, start_page

        display_title = shorten_title(row["title"])
        groups.append(
            {
                "index": index,
                "title": display_title,
                "source_title": row["title"],
                "start_page": start_page,
                "end_page": end_page,
                "row_evidence": 1,
                "page_ranges_raw": [(row["printed_start"], row["printed_end"])],
                "method": "plan_text",
                "context": [row["context"]] if row["context"] else [],
                "detected_level": "detail",
            }
        )

    return groups, auto_offset


def is_probably_overview_title(text: str) -> bool:
    normalized = normalize_space(text)
    if not normalized or len(normalized) > 40:
        return False
    if normalized in OVERVIEW_TITLE_KEYWORDS:
        return False
    if any(keyword in normalized for keyword in ("차시", "학습 목표", "교수", "평가", "각론", "교과서")):
        return False
    if parse_page_ranges(normalized):
        return False
    return True


def extract_overview_title(lines: list[str]) -> str | None:
    for index, line in enumerate(lines[:12]):
        if not any(keyword in line for keyword in OVERVIEW_TITLE_KEYWORDS):
            continue

        if index > 1 and lines[index - 1].startswith("(") and is_probably_overview_title(lines[index - 2]):
            combined = normalize_space(f"{lines[index - 2]} {lines[index - 1]}")
            if is_probably_overview_title(combined):
                return combined

        if index > 0 and is_probably_overview_title(lines[index - 1]):
            return lines[index - 1]

        stripped = normalize_space(
            line.replace("단원 개관", "").replace("제재 개관", "")
        )
        if is_probably_overview_title(stripped):
            return stripped

    return None


def detect_overview_kind(lines: list[str]) -> str:
    header = " ".join(lines[:12])
    if "단원 개관" in header:
        return "unit"
    if "제재 개관" in header:
        return "detail"
    return "detail"


def extract_overview_parent_title(lines: list[str]) -> str | None:
    for line in reversed(lines[-12:]):
        match = OVERVIEW_PARENT_RE.match(line)
        if not match:
            continue
        title = normalize_toc_title(match.group(2))
        if is_probably_overview_title(title):
            return title
    return None


def build_groups_from_overview_pages(pdf_doc) -> list[dict]:
    total_pages = len(pdf_doc.pages)
    starts: list[tuple[int, str, str]] = []

    for page_index in range(total_pages):
        text = extract_page_text(pdf_doc.pages[page_index])
        if not text:
            continue

        lines = [normalize_space(line) for line in text.splitlines() if normalize_space(line)]
        if not lines:
            continue
        if not any(
            any(keyword in line for keyword in OVERVIEW_TITLE_KEYWORDS)
            for line in lines[:12]
        ):
            continue

        title = extract_overview_title(lines)
        if not title:
            continue
        kind = detect_overview_kind(lines)
        parent_title = title if kind == "unit" else extract_overview_parent_title(lines)
        starts.append((page_index + 1, title, kind, parent_title or ""))

    deduped_starts: list[tuple[int, str, str, str]] = []
    seen: set[tuple[int, str, str, str]] = set()
    for start_page, title, kind, parent_title in starts:
        key = (start_page, title, kind, parent_title)
        if key in seen:
            continue
        seen.add(key)
        deduped_starts.append((start_page, title, kind, parent_title))

    if len(deduped_starts) < 1:
        return []

    groups: list[dict] = []
    first_start = deduped_starts[0][0]
    if first_start > 1:
        groups.append(
            {
                "index": 1,
                "title": "앞부분",
                "source_title": "앞부분",
                "start_page": 1,
                "end_page": first_start - 1,
                "row_evidence": 1,
                "page_ranges_raw": [(1, first_start - 1)],
                "method": "overview_leading_section",
                "context": [],
                "detected_level": "section",
            }
        )

    start_index = len(groups) + 1
    for offset_index, (start_page, title, kind, parent_title) in enumerate(deduped_starts, start=start_index):
        next_start = (
            deduped_starts[offset_index - start_index + 1][0]
            if offset_index - start_index + 1 < len(deduped_starts)
            else total_pages + 1
        )
        groups.append(
            {
                "index": offset_index,
                "title": shorten_title(title),
                "source_title": title,
                "start_page": start_page,
                "end_page": max(start_page, next_start - 1),
                "row_evidence": 1,
                "page_ranges_raw": [(start_page, start_page)],
                "method": "overview_page",
                "context": [],
                "detected_level": kind,
                "parent_unit_title": parent_title or None,
            }
        )

    return groups


def build_unit_groups_from_overview(groups: list[dict]) -> list[dict]:
    result: list[dict] = []
    leading_groups = [group for group in groups if group.get("detected_level") == "section"]
    result.extend(clone_group(group) for group in leading_groups)

    content_groups = [group for group in groups if group.get("detected_level") != "section"]
    if not content_groups:
        return result or [clone_group(group) for group in groups]

    unit_segments: list[dict] = []
    current_segment: dict | None = None

    for group in content_groups:
        unit_title = group.get("parent_unit_title") or (
            group["title"] if group.get("detected_level") == "unit" else None
        )
        if not unit_title:
            unit_title = current_segment["source_title"] if current_segment else group["title"]

        if current_segment is None or current_segment["source_title"] != unit_title:
            if current_segment is not None:
                unit_segments.append(current_segment)
            current_segment = clone_group(group)
            current_segment["title"] = shorten_title(unit_title)
            current_segment["source_title"] = unit_title
            current_segment["method"] = "overview_unit"
            current_segment["detected_level"] = "unit"
            current_segment["parent_unit_title"] = unit_title
        else:
            current_segment["end_page"] = max(current_segment["end_page"], group["end_page"])
            current_segment["row_evidence"] += group.get("row_evidence", 0)
            current_segment["page_ranges_raw"].extend(group.get("page_ranges_raw", []))

    if current_segment is not None:
        unit_segments.append(current_segment)

    result.extend(unit_segments)
    return result


def apply_split_level(groups: list[dict], strategy_used: str, split_level: str) -> list[dict]:
    detailed_groups = [clone_group(group) for group in groups]
    if split_level == "detail":
        return renumber_groups(detailed_groups)

    if strategy_used == "overview_page":
        return renumber_groups(build_unit_groups_from_overview(detailed_groups))

    if strategy_used == "toc":
        unit_groups = []
        for group in detailed_groups:
            detected_level = group.get("detected_level")
            if detected_level == "section":
                unit_groups.append(group)
                continue
            if detected_level in {"subunit", "project"}:
                unit_groups.append(group)
        if unit_groups:
            return renumber_groups(unit_groups)

    return renumber_groups(detailed_groups)


def choose_groups(
    pdf_doc,
    scan_pages: int,
    page_offset: int,
    z_col: int | None,
    strategy: str,
    split_level: str,
) -> tuple[list[dict], list[dict], str, int]:
    if strategy in {"auto", "toc"}:
        toc_entries = find_toc_entries(pdf_doc, scan_pages=scan_pages)
        toc_groups, toc_sections, auto_offset = build_groups_from_toc_entries(pdf_doc, toc_entries, page_offset)
        if toc_groups:
            return toc_groups, toc_sections, "toc", auto_offset
        if strategy == "toc":
            return [], [], "toc", auto_offset

    if strategy == "plan_table":
        plan_groups, auto_offset = build_groups_from_plan_tables(
            pdf_doc,
            scan_pages=scan_pages,
            page_offset=page_offset,
            z_col=z_col,
        )
        if plan_groups:
            return plan_groups, [], "plan_table", auto_offset
        plan_text_groups, auto_offset = build_groups_from_plan_text(
            pdf_doc,
            scan_pages=scan_pages,
            page_offset=page_offset,
        )
        if plan_text_groups:
            return plan_text_groups, [], "plan_text", auto_offset
        return [], [], "plan_table", 0

    if strategy == "overview":
        overview_groups = build_groups_from_overview_pages(pdf_doc)
        if overview_groups:
            return overview_groups, [], "overview_page", 0
        return [], [], "overview", 0

    if split_level == "detail":
        overview_groups = build_groups_from_overview_pages(pdf_doc)
        preferred_first_start = None
        content_overview_groups = [
            group for group in overview_groups if group.get("detected_level") != "section"
        ]
        if len(content_overview_groups) == 1:
            preferred_first_start = content_overview_groups[0]["start_page"]

        plan_groups, auto_offset = build_groups_from_plan_tables(
            pdf_doc,
            scan_pages=scan_pages,
            page_offset=page_offset,
            z_col=z_col,
        )
        if plan_groups:
            return plan_groups, [], "plan_table", auto_offset

        plan_text_groups, auto_offset = build_groups_from_plan_text(
            pdf_doc,
            scan_pages=scan_pages,
            page_offset=page_offset,
            preferred_first_start=preferred_first_start,
        )
        if plan_text_groups:
            return plan_text_groups, [], "plan_text", auto_offset

        if overview_groups:
            return overview_groups, [], "overview_page", 0
    else:
        overview_groups = build_groups_from_overview_pages(pdf_doc)
        if overview_groups:
            return overview_groups, [], "overview_page", 0

        plan_groups, auto_offset = build_groups_from_plan_tables(
            pdf_doc,
            scan_pages=scan_pages,
            page_offset=page_offset,
            z_col=z_col,
        )
        if plan_groups:
            return plan_groups, [], "plan_table", auto_offset

        plan_text_groups, auto_offset = build_groups_from_plan_text(
            pdf_doc,
            scan_pages=scan_pages,
            page_offset=page_offset,
        )
        if plan_text_groups:
            return plan_text_groups, [], "plan_text", auto_offset

    return [], [], strategy, 0


def split_subunits_from_plan_table(
    pdf_path: str | Path,
    out_dir: str | Path,
    *,
    dry_run: bool = True,
    save: bool = False,
    scan_pages: int = 60,
    page_offset: int = 0,
    z_col: int | None = None,
    strategy: str = "auto",
    split_level: str = "unit",
) -> list[dict]:
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_file}")

    if not dry_run and not save:
        dry_run = True

    output_root = Path(out_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    run_name = build_run_directory_name(pdf_file)
    run_dir = output_root / run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    groups_path = run_dir / "groups.json"

    pdfplumber = load_pdfplumber()
    with pdfplumber.open(str(pdf_file)) as pdf_doc:
        detected_groups, sections, strategy_used, auto_offset = choose_groups(
            pdf_doc,
            scan_pages=scan_pages,
            page_offset=page_offset,
            z_col=z_col,
            strategy=strategy,
            split_level=split_level,
        )
        total_pages = len(pdf_doc.pages)

    groups = apply_split_level(detected_groups, strategy_used=strategy_used, split_level=split_level)

    if not groups:
        raise RuntimeError(
            "No split groups were detected. Try a different strategy or adjust the guide-page column."
        )

    for group in groups:
        group["start_page"] = max(1, min(total_pages, group["start_page"]))
        group["end_page"] = max(1, min(total_pages, group["end_page"]))
        if group["end_page"] < group["start_page"]:
            group["start_page"], group["end_page"] = group["end_page"], group["start_page"]

    with groups_path.open("w", encoding="utf-8") as file_obj:
        json.dump(
            {
                "pdf": pdf_file.name,
                "strategy": strategy_used,
                "split_level": split_level,
                "requested_page_offset": page_offset,
                "auto_page_offset": auto_offset,
                "effective_page_offset": page_offset + auto_offset,
                "sections": sections,
                "detected_groups": detected_groups,
                "groups": groups,
            },
            file_obj,
            ensure_ascii=False,
            indent=2,
        )

    if dry_run or not save:
        return groups

    splits_dir = run_dir / "pdf_splits"
    splits_dir.mkdir(parents=True, exist_ok=True)

    for group in groups:
        filename = build_output_filename(
            index=group["index"],
            title=group["title"],
            start_page=group["start_page"],
            end_page=group["end_page"],
        )
        extract_pdf_range(
            pdf_file,
            group["start_page"],
            group["end_page"],
            splits_dir / filename,
        )

    return groups


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Split a teacher-guide PDF by TOC pages or lesson-plan tables."
    )
    parser.add_argument("--pdf", required=True, help="Input PDF path")
    parser.add_argument("--out-dir", default="output", help="Output folder")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only detect groups and write groups.json",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Write split PDFs in addition to groups.json",
    )
    parser.add_argument(
        "--scan-pages",
        default=60,
        type=int,
        help="How many front pages to scan for TOC or lesson-plan structure",
    )
    parser.add_argument(
        "--page-offset",
        default=0,
        type=int,
        help="Manual offset applied after automatic page calibration",
    )
    parser.add_argument(
        "--z-col",
        default=None,
        type=int,
        help="Force the guide-page column index (0-based) for plan-table parsing",
    )
    parser.add_argument(
        "--strategy",
        default="auto",
        choices=("auto", "toc", "plan", "overview"),
        help="Detection strategy",
    )
    parser.add_argument(
        "--split-level",
        default="unit",
        choices=("unit", "detail"),
        help="Choose coarse unit splits or more detailed sub-splits",
    )
    return parser


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()

    strategy = "plan_table" if args.strategy == "plan" else args.strategy
    groups = split_subunits_from_plan_table(
        pdf_path=args.pdf,
        out_dir=args.out_dir,
        dry_run=args.dry_run,
        save=args.save,
        scan_pages=args.scan_pages,
        page_offset=args.page_offset,
        z_col=args.z_col,
        strategy=strategy,
        split_level=args.split_level,
    )

    print(f"[OK] detected {len(groups)} groups")
    for group in groups:
        print(
            f"- {group['index']:02d}. {group['title']} "
            f"(p.{group['start_page']}-{group['end_page']}, {group['method']})"
        )

    if args.save:
        print("[OK] split PDFs were created.")
    else:
        print("[INFO] preview only. Re-run with --save to create PDFs.")


if __name__ == "__main__":
    main()
