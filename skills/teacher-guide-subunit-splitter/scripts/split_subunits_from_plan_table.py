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
import shutil
import sys
import hashlib
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

CACHE_SCHEMA_VERSION = "2026-04-01-music-plan-v2"

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
TOC_HEADING_KEYWORDS = ("차례", "목차")
TOC_ACTION_HINTS = (
    "알아봅시다",
    "알아볼까요",
    "해 볼까요",
    "해 봅시다",
    "보세요",
    "구해 봅시다",
    "찾아봅시다",
    "완성하고",
)
DISPLAY_TITLE_STOP_LINES = {"학습 안내", "활동 안내", "차시", "교과서", "쪽"}
DISPLAY_TITLE_SKIP_HINTS = (
    "교수 · 학습 과정안",
    "교수·학습 과정안",
    "과정 중심 평가 예시",
    "교과 역량 평가 계획",
)
MAX_TITLE_LENGTH = 80
MAX_FILENAME_TITLE_LENGTH = 40
MAX_TOC_SCAN_PAGES = 24
MAX_TOC_BLOCK_PAGES = 4
MAX_AUTO_OFFSET = 12
MAX_PLAN_TABLE_AUTO_OFFSET = 80
MAX_TOC_START_ADJUST_PAGES = 4
MAX_ABSORBED_LEADING_GAP_PAGES = 4
MAX_ABSORBED_MIDDLE_GAP_PAGES = 2
MAX_ABSORBED_TRAILING_GAP_PAGES = 2
LOCAL_DETAIL_EXCLUDE_TITLE_HINTS = (
    "구성 체제",
    "활용 방안",
    "개정의 방향",
    "핵심역량과",
    "교과 지식",
    "교수 학습 방법",
    "교수·학습 방법",
    "평가 방법",
    "수행 평가",
    "서술형 평가",
    "정답과 풀이",
    "자료 수록 목록",
    "학기별 지도 계획",
    "전자책등",
    "지도서",
)
UNIT_START_STRONG_HINTS = (
    "교육과정",
    "핵심 아이디어",
    "단원 소개",
    "단원의 개관",
    "제재 개관",
)
UNIT_START_SUPPORT_HINTS = (
    "단원의 학습 목표",
    "단원의 흐름",
    "단원 지도 계획",
    "교과 역량 평가 계획",
    "단원 배경지식",
)
PLAN_TITLE_ENDINGS = (
    "알아볼까요",
    "살펴볼까요",
    "이야기해 볼까요",
    "표현해 볼까요",
    "찾아볼까요",
    "무엇일까요",
    "볼까요",
    "확인해요",
    "완성해요",
    "함께해요",
    "펼쳐요",
)
PLAN_TEXT_STOP_MARKERS = (
    "[",
    "과과정정 중중심심 평평가가",
    "과정 중심 평가",
    "성취 기준별 성취 수준",
    "성성취취 기기준준",
    "큐알 코드 목록",
    "※ 성취 기준별",
)
PLAN_TITLE_INCOMPLETE_ENDINGS = (
    "알아",
    "이야",
    "표현해",
    "찾아",
    "비교해",
    "주는",
    "있는",
    "여러",
    "장소를",
    "도움을",
    "조건을",
    "방안을",
)
PLAN_TITLE_JOINABLE_TAILS = ("알아", "이야", "표현해", "찾아", "비교해")
ACTIVITY_PLAN_HEADER_MARKERS = (
    "표현 활동명",
    "표현 활동별 배당 시수",
    "활동별 합",
    "지도서 쪽수",
    "교과서 쪽수",
)
ACTIVITY_PLAN_SKIP_LINE_HINTS = (
    "시수 총합",
    "초등 미술 교과서",
    "3, 4학년 연간 학습 지도 계획",
    "지도의 실제",
    "총론",
)
ACTIVITY_PLAN_SKIP_TITLE_HINTS = (
    "미술 시간 계획표",
    "연간 학습 지도 계획",
)
ACTIVITY_PLAN_PROJECT_PARTS = {"프로", "젝트"}
MUSIC_PLAN_HEADER_MARKERS = (
    "단원 교수·학습 계획",
    "제재명",
    "차시",
    "지도서",
    "쪽수",
)
MUSIC_PLAN_SKIP_TITLE_HINTS = (
    "평가 계획",
    "수업 도움 자료",
    "단원 교수·학습 계획",
    "제재 개관",
    "단원 개관",
)

GRADE_LINE_RE = re.compile(r"^\s*([1-6])\s*학년\s*$")
TRAILING_PAGE_RE = re.compile(r"^(?P<title>.+?)\s+(?P<page>\d{1,3})$")
OVERVIEW_PARENT_RE = re.compile(r"^\s*(\d{1,2})\.\s*(.+?)\s*$")
PLAN_RANGE_AT_END_RE = re.compile(r"(?P<range>\d{1,3}\s*[~-]\s*\d{1,3})\s*$")
ACTIVITY_PLAN_HOURS_RE = re.compile(r"^\(?\s*(\d+)\s*\)?$")
MUSIC_PLAN_PAGE_RE = re.compile(r"\d{1,3}")


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


def build_output_filename(index: int, title: str, start_page: int, end_page: int, pdf_name: str = "", parent_title: str | None = None) -> str:
    title_part = sanitize_filename_part(shorten_title(title, max_chars=MAX_FILENAME_TITLE_LENGTH))
    
    if parent_title and parent_title != title:
        parent_part = sanitize_filename_part(shorten_title(parent_title, max_chars=20))
        title_part = f"{parent_part}_{title_part}"
        
    page_part = f"p{start_page}-{end_page}"
    prefix = ""
    if pdf_name:
        base = Path(pdf_name).stem
        prefix = f"[{base}]_"
    if title_part:
        return f"{prefix}subunit_{index:02d}_{title_part}_{page_part}.pdf"
    return f"{prefix}subunit_{index:02d}_{page_part}.pdf"


def build_run_directory_name(pdf_path: str | Path) -> str:
    return sanitize_filename_part(Path(pdf_path).stem)[:50] or "teacher_guide"


def ensure_directory_within_root(target_dir: str | Path, root_dir: str | Path) -> Path:
    resolved_target = Path(target_dir).resolve()
    resolved_root = Path(root_dir).resolve()
    try:
        resolved_target.relative_to(resolved_root)
    except ValueError as exc:
        raise RuntimeError(f"Refusing to operate outside output root: {resolved_target}") from exc
    return resolved_target


def resolve_run_directory(
    output_root: str | Path,
    pdf_path: str | Path,
    *,
    existing_run_dir: str = "reuse",
    create: bool = True,
) -> Path:
    output_root_path = Path(output_root)
    output_root_path.mkdir(parents=True, exist_ok=True)

    run_name = build_run_directory_name(pdf_path)
    base_run_dir = output_root_path / run_name
    mode = existing_run_dir.lower()
    if mode not in {"reuse", "replace", "suffix"}:
        raise ValueError(f"Unknown existing-run-dir mode: {existing_run_dir}")

    run_dir = base_run_dir
    if mode == "replace" and base_run_dir.exists():
        if not base_run_dir.is_dir():
            raise RuntimeError(f"Existing output path is not a folder: {base_run_dir}")
        safe_run_dir = ensure_directory_within_root(base_run_dir, output_root_path)
        shutil.rmtree(safe_run_dir)
    elif mode == "suffix" and base_run_dir.exists():
        suffix_index = 1
        while True:
            candidate = output_root_path / f"{run_name} ({suffix_index})"
            if not candidate.exists():
                run_dir = candidate
                break
            suffix_index += 1

    if create:
        run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


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


def squash_heading_text(text: str) -> str:
    return re.sub(r"\s+", "", normalize_space(text))


def has_toc_heading(text: str) -> bool:
    squashed = squash_heading_text(text)
    return any(keyword in squashed for keyword in TOC_HEADING_KEYWORDS)


def is_part_heading_line(line: str) -> bool:
    return bool(re.fullmatch(r"(?:PART|Part)\s+\d+", normalize_space(line)))


def contains_meaningful_title_chars(title: str) -> bool:
    return bool(re.search(r"[A-Za-z가-힣ⅠⅡⅢⅣⅤ]", title))


def looks_like_activity_sentence(title: str) -> bool:
    if "준비물" in title:
        return True
    if re.search(r"활동\s*\d", title):
        return True
    return len(title) > 18 and any(hint in title for hint in TOC_ACTION_HINTS)


def is_probably_toc_title(title: str) -> bool:
    if not title:
        return False
    if len(title) < 2 or len(title) > 60:
        return False
    if not contains_meaningful_title_chars(title):
        return False
    if re.search(r"\d{1,3}\s*[-~]\s*\d{1,3}", title):
        return False
    if re.fullmatch(r"[0-9\s+_=<>~./()\-]+", title):
        return False
    if title.count(" ") > 10:
        return False
    if sum(char.isdigit() for char in title) > 4:
        return False
    if looks_like_activity_sentence(title):
        return False
    return True


def classify_toc_entry(title: str, context: tuple[str, ...]) -> str:
    if "계획표" in title or "지도 계획" in title:
        return "plan"
    if re.match(r"^\d{1,2}(?:\.\s*|\s)", title):
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
    pending_prefix: str | None = None

    for raw_line in text.splitlines():
        line = normalize_space(raw_line.replace("•", " ").replace("·", " "))
        if not line:
            continue

        if has_toc_heading(line):
            current_section = line
            pending_prefix = None
            continue

        if is_part_heading_line(line):
            current_section = line
            pending_prefix = None
            continue

        grade_match = GRADE_LINE_RE.match(line)
        if grade_match:
            current_grade = f"{grade_match.group(1)}학년"
            pending_prefix = None
            continue

        match = TRAILING_PAGE_RE.match(line)
        if match:
            title = normalize_toc_title(match.group("title"))
            if pending_prefix:
                merged_title = normalize_toc_title(f"{pending_prefix} {title}")
                if is_probably_toc_title(merged_title):
                    title = merged_title
            if not is_probably_toc_title(title):
                pending_prefix = None
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
            pending_prefix = None
            continue

        if len(line) <= 24 and any(hint in line for hint in TOC_SECTION_HINTS):
            current_section = line
            pending_prefix = None
            continue

        if (
            len(line) <= 40
            and contains_meaningful_title_chars(line)
            and not looks_like_activity_sentence(line)
            and not parse_page_ranges(line)
            and not re.search(r"[.!?]\s*$", line)
        ):
            pending_prefix = line

    return entries


def score_toc_page(page_text: str, entries: list[TocEntry], source_page: int) -> int:
    if len(entries) < 3:
        return -1

    pages = [entry.printed_page for entry in entries]
    ascending_pairs = sum(1 for left, right in zip(pages, pages[1:]) if right > left)
    descending_pairs = sum(1 for left, right in zip(pages, pages[1:]) if right < left)
    short_titles = sum(1 for entry in entries if len(entry.title) <= 24)
    future_pages = sum(1 for page in pages if page >= source_page + 2)
    near_pages = sum(1 for page in pages if page <= source_page + 1)
    numeric_titles = sum(1 for entry in entries if not contains_meaningful_title_chars(entry.title))
    noisy_titles = sum(1 for entry in entries if looks_like_activity_sentence(entry.title))

    score = len(entries) * 4
    score += ascending_pairs * 3
    score += short_titles
    score += future_pages
    score -= descending_pairs * 4
    score -= near_pages * 3
    score -= numeric_titles * 6
    score -= noisy_titles * 4

    if has_toc_heading(page_text):
        score += 12
    elif ascending_pairs < max(2, len(entries) // 2):
        score -= 12
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
    page_snapshots: list[dict] = []

    for page_index in range(limit):
        text = extract_page_text(pdf_doc.pages[page_index])
        entries = extract_toc_entries_from_text(text, source_page=page_index + 1)
        page_snapshots.append(
            {
                "page_index": page_index,
                "entries": entries,
                "score": score_toc_page(text, entries, source_page=page_index + 1),
                "has_heading": has_toc_heading(text),
            }
        )

    heading_page = next((snapshot["page_index"] for snapshot in page_snapshots if snapshot["has_heading"]), None)
    if heading_page is not None:
        candidates: list[TocEntry] = []
        for snapshot in page_snapshots[heading_page : heading_page + MAX_TOC_BLOCK_PAGES]:
            if snapshot["has_heading"] or snapshot["score"] >= 18:
                candidates.extend(snapshot["entries"])
                continue
            if candidates:
                break
        deduped = dedupe_toc_entries(candidates)
        if deduped:
            return deduped

    fallback_candidates: list[TocEntry] = []
    for snapshot in page_snapshots:
        if snapshot["score"] >= 28:
            fallback_candidates.extend(snapshot["entries"])

    return dedupe_toc_entries(fallback_candidates)


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


def page_looks_like_toc_listing(pdf_doc, page_number: int) -> bool:
    if page_number < 1 or page_number > len(pdf_doc.pages):
        return False
    text = extract_page_text(pdf_doc.pages[page_number - 1])
    if not text:
        return False
    entries = extract_toc_entries_from_text(text, source_page=page_number)
    if not entries:
        return False
    return has_toc_heading(text) or score_toc_page(text, entries, source_page=page_number) >= 18


def page_has_heading_prefix(lines: list[str], title: str) -> bool:
    normalized_title = normalize_toc_title(title)
    stripped_title = normalize_toc_title(re.sub(r"^\d{1,2}(?:\.\s*|\s)+", "", normalized_title))
    canonical_title = normalize_toc_title(normalized_title.replace(".", " "))
    canonical_stripped = normalize_toc_title(stripped_title.replace(".", " "))
    for line in lines[:3]:
        normalized_line = normalize_toc_title(line)
        canonical_line = normalize_toc_title(normalized_line.replace(".", " "))
        if canonical_stripped and canonical_line.startswith(canonical_stripped):
            return True
        if canonical_title and canonical_line.startswith(canonical_title):
            return True
    return False


def page_has_strong_title_signal(pdf_doc, page_number: int, title: str) -> bool:
    if page_number < 1 or page_number > len(pdf_doc.pages):
        return False

    text = extract_page_text(pdf_doc.pages[page_number - 1])
    lines = [normalize_space(line) for line in text.splitlines() if normalize_space(line)]
    if page_looks_like_toc_listing(pdf_doc, page_number):
        return page_has_heading_prefix(lines, title) and not any(TRAILING_PAGE_RE.match(line) for line in lines[1:4])

    top_text = normalize_toc_title(" ".join(lines[:40]))
    if not top_text:
        return False

    if page_has_heading_prefix(lines, title):
        return True

    tokens = entry_search_tokens(title)
    heading_markers = ("단원명", "학습 목표", "핵심 아이디어", "과정안", "성취기준")
    if len(tokens) >= 2 and all(token in top_text for token in tokens[:2]) and any(marker in top_text for marker in heading_markers):
        return True
    return False


def page_looks_like_detail_lead_in(pdf_doc, page_number: int) -> bool:
    if page_number < 1 or page_number > len(pdf_doc.pages):
        return False
    if page_looks_like_toc_listing(pdf_doc, page_number):
        return False

    text = extract_page_text(pdf_doc.pages[page_number - 1])
    lines = [normalize_space(line) for line in text.splitlines() if normalize_space(line)]
    top_lines = lines[:12]
    top_text = " ".join(top_lines)
    bullet_count = sum(1 for line in top_lines if line.startswith("•"))
    if any(re.match(r"^\d+(?:[~∼]\d+)?차시(?:\s|$)", line) for line in top_lines[:3]):
        return "핵심 아이디어" in top_text and "학습 목표" in top_text
    return "핵심 아이디어" in top_text and "학습 목표" in top_text and bullet_count >= 1


def align_toc_entry_start_page(
    pdf_doc,
    title: str,
    start_page: int,
    *,
    max_page: int,
) -> int:
    if start_page >= max_page:
        return start_page

    strong_page: int | None = None
    search_end = min(max_page, start_page + MAX_TOC_START_ADJUST_PAGES)
    for page_number in range(start_page, search_end + 1):
        if page_has_strong_title_signal(pdf_doc, page_number, title):
            strong_page = page_number
            break

    if strong_page is None:
        return start_page

    candidate = strong_page
    previous_page = strong_page - 1
    if previous_page >= start_page and page_looks_like_detail_lead_in(pdf_doc, previous_page):
        candidate = previous_page
    return candidate


def align_toc_entry_starts(pdf_doc, entries: list[dict]) -> list[dict]:
    if not entries:
        return []

    aligned_entries: list[dict] = []
    total_pages = len(pdf_doc.pages)

    for index, entry in enumerate(entries):
        next_start = entries[index + 1]["start_page"] if index + 1 < len(entries) else total_pages + 1
        min_allowed = aligned_entries[-1]["start_page"] + 1 if aligned_entries else 1
        max_allowed = max(min_allowed, next_start - 1)
        aligned_start = align_toc_entry_start_page(
            pdf_doc,
            entry["title"],
            entry["start_page"],
            max_page=max_allowed,
        )
        cloned = dict(entry)
        cloned["start_page"] = max(min_allowed, min(aligned_start, max_allowed))
        aligned_entries.append(cloned)

    return aligned_entries


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
    leaf_entries = align_toc_entry_starts(pdf_doc, leaf_entries)

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
        display_title = resolve_display_title_from_page_heading(
            pdf_doc,
            entry["start_page"],
            entry["title"],
        )
        groups.append(
            {
                "index": offset_index,
                "title": display_title,
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

    section_source_entries = leaf_entries if leaf_entries else valid_entries
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


def is_suspicious_group_title(title: str) -> bool:
    normalized = normalize_toc_title(title)
    if not normalized:
        return True
    if not contains_meaningful_title_chars(normalized):
        return True
    if title_needs_page_heading_rescue(normalized):
        return True
    if looks_like_activity_sentence(normalized):
        return True
    if re.fullmatch(r"[0-9\s+_=<>~./()\-]+", normalized):
        return True
    return False


def toc_groups_look_reasonable(groups: list[dict]) -> bool:
    content_groups = [group for group in groups if group.get("detected_level") != "section"]
    if len(content_groups) < 3:
        return False

    suspicious_titles = sum(1 for group in content_groups if is_suspicious_group_title(group["title"]))
    single_page_groups = sum(1 for group in content_groups if group["start_page"] == group["end_page"])
    if suspicious_titles >= max(2, len(content_groups) // 3):
        return False
    if len(content_groups) >= 6 and single_page_groups > len(content_groups) // 2:
        return False
    return True


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


def page_index_window(total_pages: int, start_page: int | None = None, end_page: int | None = None) -> range:
    start_index = max(0, (start_page - 1) if start_page is not None else 0)
    end_index = min(total_pages - 1, (end_page - 1) if end_page is not None else total_pages - 1)
    if end_index < start_index:
        return range(0, 0)
    return range(start_index, end_index + 1)


def find_plan_table_pages(
    pdf_doc,
    scan_pages: int,
    title_keywords: Iterable[str],
    start_page: int | None = None,
    end_page: int | None = None,
) -> list[int]:
    total_pages = len(pdf_doc.pages)
    candidate_indices = list(page_index_window(total_pages, start_page=start_page, end_page=end_page))
    if not candidate_indices:
        return []
    if scan_pages > 0:
        candidate_indices = candidate_indices[:scan_pages]
    keywords = [keyword.lower() for keyword in title_keywords]

    matches: list[int] = []
    for page_index in candidate_indices:
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


def table_page_range_hits(table: list[list[str | None]]) -> int:
    return sum(
        len(parse_page_ranges(normalize_space(cell)))
        for row in table
        for cell in row
        if normalize_space(cell)
    )


def table_title_row_hits(table: list[list[str | None]]) -> int:
    hits = 0
    for row in table:
        if not row:
            continue
        title = normalize_space(row[0] if row else "")
        if is_probably_group_title(title):
            hits += 1
    return hits


def best_spread_candidate_table(tables: list[list[list[str | None]]]) -> list[list[str | None]] | None:
    if not tables:
        return None
    return max(
        tables,
        key=lambda table: (
            table_page_range_hits(table),
            table_title_row_hits(table),
            len(table),
            max((len(row) for row in table), default=0),
        ),
    )


def trim_spread_right_rows(table: list[list[str | None]]) -> list[list[str | None]]:
    rows = [row for row in table if any(normalize_space(cell) for cell in row)]
    while rows and not any(parse_page_ranges(normalize_space(cell)) for cell in rows[0] if normalize_space(cell)):
        rows = rows[1:]
    return rows


def can_merge_spread_tables(
    left_table: list[list[str | None]],
    right_table: list[list[str | None]],
) -> bool:
    left_rows = [row for row in left_table if any(normalize_space(cell) for cell in row)]
    right_rows = trim_spread_right_rows(right_table)
    if len(left_rows) < 4 or len(right_rows) < 4:
        return False

    left_title_hits = table_title_row_hits(left_rows)
    left_range_hits = table_page_range_hits(left_rows)
    right_range_hits = table_page_range_hits(right_rows)
    right_leading_blank_rows = sum(
        1
        for row in right_rows
        if not normalize_space(row[0] if len(row) > 0 else "")
        and not normalize_space(row[1] if len(row) > 1 else "")
    )
    return (
        left_title_hits >= max(3, len(left_rows) // 2)
        and left_range_hits <= max(2, len(left_rows) // 4)
        and right_range_hits >= max(3, len(right_rows) // 2)
        and right_leading_blank_rows >= max(3, len(right_rows) // 2)
        and abs(len(left_rows) - len(right_rows)) <= 1
    )


def merge_spread_tables(
    left_table: list[list[str | None]],
    right_table: list[list[str | None]],
) -> list[list[str | None]] | None:
    if not can_merge_spread_tables(left_table, right_table):
        return None

    left_rows = [row for row in left_table if any(normalize_space(cell) for cell in row)]
    right_rows = trim_spread_right_rows(right_table)
    row_count = min(len(left_rows), len(right_rows))
    if row_count < 4:
        return None

    merged: list[list[str | None]] = [
        ["단원 지도 계획", "", "", "", "", "", "", ""],
        ["주제", "수업 내용 및 활동", "교과 역량", "준비물", "교과서", "지도서", "평가 방법", "평가 내용"],
    ]

    def cell(row: list[str | None], index: int) -> str:
        return normalize_space(row[index] if index < len(row) else "")

    for index in range(row_count):
        left_row = left_rows[index]
        right_row = right_rows[index]
        merged.append(
            [
                cell(left_row, 0),
                cell(left_row, 1),
                cell(left_row, 2),
                cell(right_row, 2),
                cell(right_row, 3),
                cell(right_row, 4),
                cell(right_row, 5),
                cell(right_row, 6),
            ]
        )

    return merged


def merge_spread_tables_by_page(
    extracted_by_page: list[tuple[int, list[list[str | None]]]],
) -> tuple[list[list[list[str | None]]], set[int]]:
    tables_by_page: dict[int, list[list[list[str | None]]]] = defaultdict(list)
    for page_index, table in extracted_by_page:
        tables_by_page[page_index].append(table)

    merged_tables: list[list[list[str | None]]] = []
    merged_pages: set[int] = set()
    sorted_pages = sorted(tables_by_page)
    for page_index in sorted_pages:
        next_page = page_index + 1
        if next_page not in tables_by_page:
            continue
        left_table = best_spread_candidate_table(tables_by_page[page_index])
        right_table = best_spread_candidate_table(tables_by_page[next_page])
        if not left_table or not right_table:
            continue
        merged_table = merge_spread_tables(left_table, right_table)
        if merged_table:
            merged_tables.append(merged_table)
            merged_pages.update({page_index, next_page})

    return merged_tables, merged_pages


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
    groups: list[dict] = []
    current_group: dict | None = None

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
                if current_group is None or current_group["title"] != row_title:
                    current_group = {
                        "title": row_title,
                        "page_ranges": [],
                        "row_evidence": 0,
                    }
                    groups.append(current_group)

            if not current_group or not guide_cell:
                continue

            page_ranges = parse_page_ranges(guide_cell)
            if not page_ranges:
                continue

            current_group["page_ranges"].extend(page_ranges)
            current_group["row_evidence"] += 1

    final_groups: list[dict] = []
    for group in groups:
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


def count_valid_plan_table_groups(groups: list[dict], offset: int, total_pages: int) -> int:
    return sum(
        1
        for group in groups
        if 1 <= group["start_page"] + offset <= group["end_page"] + offset <= total_pages
    )


def score_plan_table_offset(pdf_doc, groups: list[dict], offset: int) -> int:
    total_pages = len(pdf_doc.pages)
    valid_groups: list[tuple[dict, int, int]] = []
    invalid_group_count = 0

    for group in groups:
        start_page = group["start_page"] + offset
        end_page = group["end_page"] + offset
        if 1 <= start_page <= end_page <= total_pages:
            valid_groups.append((group, start_page, end_page))
        else:
            invalid_group_count += 1

    if not valid_groups:
        return -10_000

    score = len(valid_groups) * 6
    score -= invalid_group_count * 12
    score -= abs(offset)

    mapped_starts = [start_page for _, start_page, _ in valid_groups]
    score += sum(1 for left, right in zip(mapped_starts, mapped_starts[1:]) if right > left)

    for group, start_page, _ in valid_groups[:6]:
        if entry_matches_page(pdf_doc, start_page, entry_search_tokens(group["title"])):
            score += 8

    return score


def infer_plan_table_page_offset(pdf_doc, groups: list[dict]) -> int:
    total_pages = len(pdf_doc.pages)
    if not groups:
        return 0

    first_start = min(group["start_page"] for group in groups)
    last_end = max(group["end_page"] for group in groups)
    search_limit = max(
        MAX_AUTO_OFFSET,
        first_start - 1,
        max(0, last_end - total_pages),
        max(0, total_pages - last_end),
    )
    search_limit = min(MAX_PLAN_TABLE_AUTO_OFFSET, search_limit)

    zero_valid = count_valid_plan_table_groups(groups, 0, total_pages)
    if zero_valid >= max(3, len(groups) // 2):
        candidate_offsets = [0] + [
            offset for offset in range(-search_limit, search_limit + 1) if offset != 0
        ]
    else:
        candidate_offsets = list(range(-search_limit, search_limit + 1))

    best_offset = 0
    best_score = -10_000
    for offset in candidate_offsets:
        offset_score = score_plan_table_offset(pdf_doc, groups, offset)
        if offset_score > best_score:
            best_score = offset_score
            best_offset = offset

    return best_offset


def build_groups_from_plan_tables(
    pdf_doc,
    scan_pages: int,
    page_offset: int,
    z_col: int | None,
    start_page: int | None = None,
    end_page: int | None = None,
) -> tuple[list[dict], int]:
    total_pages = len(pdf_doc.pages)
    window_page_count = len(list(page_index_window(len(pdf_doc.pages), start_page=start_page, end_page=end_page)))
    candidate_scan_pages = window_page_count if start_page is None and end_page is None else scan_pages
    candidate_pages = find_plan_table_pages(
        pdf_doc,
        scan_pages=candidate_scan_pages,
        title_keywords=PLAN_TITLE_KEYWORDS,
        start_page=start_page,
        end_page=end_page,
    )
    if not candidate_pages and candidate_scan_pages != window_page_count:
        candidate_pages = find_plan_table_pages(
            pdf_doc,
            scan_pages=window_page_count,
            title_keywords=PLAN_TITLE_KEYWORDS,
            start_page=start_page,
            end_page=end_page,
        )
    if not candidate_pages:
        return [], 0

    extracted_tables: list[list[list[str | None]]] = []
    extracted_by_page: list[tuple[int, list[list[str | None]]]] = []
    pages_to_extract = sorted(
        {
            page_index
            for candidate_page in candidate_pages
            for page_index in (candidate_page, candidate_page + 1)
            if 0 <= page_index < len(pdf_doc.pages)
            and (start_page is None or page_index + 1 >= start_page)
            and (end_page is None or page_index + 1 <= end_page)
        }
    )
    for page_index in pages_to_extract:
        page_tables = extract_tables_from_page(pdf_doc.pages[page_index])
        extracted_by_page.extend((page_index, table) for table in page_tables)

    merged_tables, merged_pages = merge_spread_tables_by_page(extracted_by_page)
    extracted_tables.extend(table for page_index, table in extracted_by_page if page_index not in merged_pages)
    extracted_tables.extend(merged_tables)
    if not extracted_tables:
        return [], 0

    scored_tables = [
        (score_table_for_plan(table), index, table)
        for index, table in enumerate(extracted_tables)
    ]
    selected_tables = sorted(
        (item for item in scored_tables if item[0] > 0),
        key=lambda item: item[1],
    )
    top_tables = [table for _, _, table in selected_tables]
    parsed_groups = build_groups_from_tables(top_tables, guide_column_override=z_col)
    if not parsed_groups:
        return [], 0
    auto_offset = infer_plan_table_page_offset(pdf_doc, parsed_groups)
    effective_offset = auto_offset + page_offset

    final_groups: list[dict] = []
    for index, group in enumerate(parsed_groups, start=1):
        start_page = group["start_page"] + effective_offset
        end_page = group["end_page"] + effective_offset
        if end_page < start_page:
            start_page, end_page = end_page, start_page
        if end_page < 1 or start_page > total_pages:
            continue
        start_page = max(1, start_page)
        end_page = min(total_pages, end_page)

        display_title = resolve_display_title_from_page_heading(
            pdf_doc,
            start_page,
            group["title"],
        )
        final_groups.append(
            {
                "index": index,
                "title": display_title,
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

    return final_groups, auto_offset


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


def strip_plan_text_explanation(text: str) -> str:
    stripped = normalize_space(PLAN_RANGE_AT_END_RE.sub("", text))
    for marker in PLAN_TEXT_STOP_MARKERS:
        if marker in stripped:
            stripped = stripped.split(marker, 1)[0].strip()
    return normalize_space(stripped)


def trim_plan_text_repeated_tail(text: str, current_title: str) -> str:
    if not text or not current_title:
        return text
    repeated_index = text.find(current_title)
    if repeated_index > 0:
        return text[:repeated_index].strip()
    return text


def extract_plan_title_fragment(text: str, current_title: str = "") -> str:
    candidate = strip_plan_text_explanation(text)
    candidate = trim_plan_text_repeated_tail(candidate, current_title)
    candidate = collapse_leading_repeated_words(candidate)
    if not candidate:
        return ""

    repeated = collapse_leading_repeated_words(candidate)
    if repeated:
        candidate = repeated

    for ending in PLAN_TITLE_ENDINGS:
        if ending in candidate:
            return candidate.split(ending, 1)[0].strip() + ending

    if "단원 도입" in candidate:
        return "단원 도입"
    if "생각을 펼쳐요" in candidate:
        return "생각을 펼쳐요"
    if "재미있게 확인해요" in candidate:
        return "재미있게 확인해요"
    if "생각 그물을 완성해요" in candidate:
        return "생각 그물을 완성해요"

    if len(candidate) <= MAX_TITLE_LENGTH:
        return candidate

    return candidate[:MAX_TITLE_LENGTH].strip()


def rough_row_title(rest: str) -> str:
    return extract_plan_title_fragment(rest)


def title_needs_conservative_completion(title: str) -> bool:
    normalized = normalize_space(title)
    if not normalized:
        return False
    if any(normalized.endswith(ending) for ending in PLAN_TITLE_ENDINGS):
        return False

    last_word = normalized.split()[-1]
    if last_word in {"도입", "만들기", "표현하기", "소개하기", "정리하기"}:
        return False
    return any(normalized.endswith(ending) for ending in PLAN_TITLE_INCOMPLETE_ENDINGS)


def is_safe_plan_title_completion(fragment: str, current_title: str) -> bool:
    normalized = normalize_space(fragment)
    if not normalized:
        return False
    if parse_page_ranges(normalized):
        return False
    if any(marker in normalized for marker in PLAN_TEXT_STOP_MARKERS):
        return False
    if "," in normalized or "，" in normalized:
        return False
    if len(normalized) > 24:
        return False

    words = normalized.split()
    if len(words) == 1:
        return current_title.endswith(PLAN_TITLE_JOINABLE_TAILS) and normalized in {"볼까요", "해요"}

    if len(words) > 5:
        return False
    return any(normalized.endswith(ending) for ending in PLAN_TITLE_ENDINGS)


def combine_plan_title_fragments(title: str, fragment: str) -> str:
    normalized_title = normalize_space(title)
    normalized_fragment = normalize_space(fragment)
    if not normalized_title:
        return normalized_fragment
    if not normalized_fragment or normalized_fragment in normalized_title:
        return normalized_title

    title_words = normalized_title.split()
    fragment_words = normalized_fragment.split()
    max_overlap = min(4, len(title_words), len(fragment_words))
    for overlap_size in range(max_overlap, 0, -1):
        if title_words[-overlap_size:] == fragment_words[:overlap_size]:
            fragment_words = fragment_words[overlap_size:]
            break

    if not fragment_words:
        return normalized_title
    return normalize_space(f"{normalized_title} {' '.join(fragment_words)}")


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


def title_has_connector_tail(title: str) -> bool:
    normalized = normalize_space(title)
    if not normalized:
        return False
    last_word = normalized.split()[-1]
    return last_word in {"및", "와", "과", "또는"}


def title_has_ocr_artifacts(title: str) -> bool:
    normalized = normalize_space(title)
    if not normalized:
        return False
    if normalized.count("(") != normalized.count(")"):
        return True
    if any(marker in normalized for marker in ("�", "□")):
        return True
    if re.search(r"[A-Za-z0-9가-힣)\]]\s*_\s*[A-Za-z0-9가-힣(\[]", normalized):
        return True
    return bool(re.search(r"[._/\-]{2,}", normalized))


def title_has_stable_lesson_signal(title: str) -> bool:
    normalized = normalize_space(title)
    if not normalized:
        return False
    return any(ending in normalized for ending in PLAN_TITLE_ENDINGS)


def title_needs_page_heading_rescue(title: str) -> bool:
    normalized = normalize_space(title)
    if not normalized:
        return True
    if title_has_connector_tail(normalized):
        return True
    if title_has_ocr_artifacts(normalized) and not title_has_stable_lesson_signal(normalized):
        return True
    return normalized.endswith(("(", "[", "/", "-", ":", "·"))


def extract_display_title_from_start_page(
    pdf_doc,
    start_page: int,
    fallback: str,
    *,
    parent_title: str | None = None,
) -> str:
    fallback_title = shorten_title(fallback)
    if start_page < 1 or start_page > len(pdf_doc.pages):
        return fallback_title

    text = extract_page_text(pdf_doc.pages[start_page - 1])
    lines = [normalize_space(line) for line in text.splitlines() if normalize_space(line)]
    fallback_normalized = normalize_toc_title(fallback_title)
    parent_normalized = normalize_toc_title(parent_title or "")

    for line in lines[:12]:
        if is_probably_footer_or_noise(line):
            continue
        if any(keyword in line for keyword in OVERVIEW_TITLE_KEYWORDS):
            continue
        if any(keyword in line for keyword in PLAN_TITLE_KEYWORDS):
            continue
        if line in DISPLAY_TITLE_STOP_LINES:
            continue
        if is_part_heading_line(line):
            continue
        if any(hint in line for hint in LOCAL_DETAIL_EXCLUDE_TITLE_HINTS + DISPLAY_TITLE_SKIP_HINTS):
            continue

        candidate = normalize_toc_title(line)
        if not candidate:
            continue
        if parent_normalized and candidate == parent_normalized:
            continue
        if candidate == fallback_normalized:
            continue
        return shorten_title(candidate)

    return fallback_title


def resolve_display_title_from_page_heading(
    pdf_doc,
    start_page: int,
    fallback: str,
    *,
    parent_title: str | None = None,
) -> str:
    fallback_title = shorten_title(fallback)
    if not title_needs_page_heading_rescue(fallback_title):
        return fallback_title

    return extract_display_title_from_start_page(
        pdf_doc,
        start_page,
        fallback_title,
        parent_title=parent_title,
    )


def extract_plan_rows_from_text_pages(
    pdf_doc,
    scan_pages: int,
    start_page: int | None = None,
    end_page: int | None = None,
) -> list[dict]:
    total_pages = len(pdf_doc.pages)
    rows: list[dict] = []

    candidate_indices = list(page_index_window(total_pages, start_page=start_page, end_page=end_page))
    if scan_pages > 0:
        candidate_indices = candidate_indices[:scan_pages]

    for page_index in candidate_indices:
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
                candidate_fragment = extract_plan_title_fragment(line, current_title=pending_title)
                if (
                    title_needs_conservative_completion(pending_title)
                    and is_safe_plan_title_completion(candidate_fragment, pending_title)
                ):
                    pending_title = combine_plan_title_fragments(pending_title, candidate_fragment)
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
    start_page: int | None = None,
    end_page: int | None = None,
) -> tuple[list[dict], int]:
    rows = extract_plan_rows_from_text_pages(
        pdf_doc,
        scan_pages=scan_pages,
        start_page=start_page,
        end_page=end_page,
    )
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

        display_title = resolve_display_title_from_page_heading(
            pdf_doc,
            start_page,
            row["title"],
        )
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


def normalize_activity_plan_title(text: str) -> str:
    normalized = normalize_toc_title(text)
    normalized = normalized.replace("프로 젝트", "프로젝트")
    normalized = re.sub(r"\s+([,./])", r"\1", normalized)
    normalized = re.sub(r"\(\s*(\d+)\s*\)", r"(\1)", normalized)
    return normalize_space(normalized)


def extract_word_lines_from_page(page) -> list[dict]:
    words_by_line: dict[tuple[int, int], list[tuple[float, float, float, float, str]]] = defaultdict(list)
    raw_words: list[tuple[float, float, float, float, str, int, int]] = []

    try:
        extracted_words = page.extract_words(use_text_flow=False, keep_blank_chars=False)
    except Exception:
        extracted_words = None

    if extracted_words:
        clustered_words: list[tuple[float, float, float, float, str]] = []
        for word in extracted_words:
            text = normalize_space(word.get("text"))
            if not text:
                continue
            x0 = float(word.get("x0", 0.0))
            y0 = float(word.get("top", word.get("y0", 0.0)))
            x1 = float(word.get("x1", x0))
            y1 = float(word.get("bottom", word.get("y1", y0)))
            clustered_words.append((x0, y0, x1, y1, text))

        clustered_words.sort(key=lambda item: (item[1], item[0]))
        line_index = -1
        current_y: float | None = None
        for x0, y0, x1, y1, text in clustered_words:
            if current_y is None or abs(y0 - current_y) > 3.2:
                line_index += 1
                current_y = y0
            raw_words.append((x0, y0, x1, y1, text, 0, line_index))
    else:
        for word in page.get_text("words"):
            x0, y0, x1, y1, text, block_no, line_no, _ = word
            normalized = normalize_space(text)
            if not normalized:
                continue
            raw_words.append((x0, y0, x1, y1, normalized, int(block_no), int(line_no)))

    for x0, y0, x1, y1, text, block_no, line_no in raw_words:
        words_by_line[(block_no, line_no)].append((x0, y0, x1, y1, text))

    lines: list[dict] = []
    for key, words in words_by_line.items():
        ordered = sorted(words, key=lambda item: item[0])
        text = normalize_space(" ".join(item[4] for item in ordered))
        if not text:
            continue
        lines.append(
            {
                "key": key,
                "y": min(item[1] for item in ordered),
                "text": text,
                "words": ordered,
            }
        )

    lines.sort(key=lambda item: (item["y"], item["words"][0][0]))
    return lines


def is_activity_plan_candidate_page(lines: list[dict]) -> bool:
    preview = " ".join(line["text"] for line in lines[:12])
    return all(marker in preview for marker in ACTIVITY_PLAN_HEADER_MARKERS[:3]) and "지도서" in preview and "교과서" in preview


def detect_activity_plan_columns(lines: list[dict]) -> dict[str, float] | None:
    header_lines = [line for line in lines if line["y"] <= 205]
    if not header_lines:
        return None

    header_words = [word for line in header_lines for word in line["words"]]

    def first_x(*keywords: str, min_x: float = -1.0) -> float | None:
        xs = [
            word[0]
            for word in header_words
            if word[0] >= min_x and any(keyword in word[4] for keyword in keywords)
        ]
        return min(xs) if xs else None

    unit_title_x = first_x("단원명")
    guide_x = first_x("지도서")
    activity_x = first_x("활동명", min_x=(guide_x or 0) + 20)
    textbook_x = first_x("교과서", min_x=(activity_x or 0) + 20)
    hours_x = first_x("배당", "활동별", min_x=(textbook_x or 0) + 10)
    total_x = first_x("합", min_x=(hours_x or 0) + 10)
    if None in {unit_title_x, guide_x, activity_x, textbook_x, hours_x, total_x}:
        return None

    content_words = [
        word
        for line in lines
        if line["y"] > max(header_line["y"] for header_line in header_lines) + 4
        for word in line["words"]
    ]
    guide_page_words = [
        word
        for word in content_words
        if parse_page_ranges(word[4]) and word[0] < textbook_x
    ]
    textbook_page_words = [
        word
        for word in content_words
        if parse_page_ranges(word[4]) and word[0] >= activity_x and word[0] < hours_x
    ]
    unit_number_xs = [
        word[0]
        for word in content_words
        if 60 <= word[0] < unit_title_x and (re.fullmatch(r"\d+", word[4]) or word[4] in ACTIVITY_PLAN_PROJECT_PARTS)
    ]
    if unit_number_xs:
        sorted_unit_xs = sorted(unit_number_xs)
        unit_number_x = sorted_unit_xs[len(sorted_unit_xs) // 2]
    else:
        unit_number_x = unit_title_x - 36

    guide_start_x = min((word[0] for word in guide_page_words), default=guide_x)
    guide_end_x = max((word[2] for word in guide_page_words), default=guide_start_x + 28) + 8
    textbook_start_x = min((word[0] for word in textbook_page_words), default=textbook_x)
    textbook_end_x = max((word[2] for word in textbook_page_words), default=textbook_start_x + 24) + 8

    return {
        "header_end_y": max(word[3] for word in header_words),
        "unit_number_end": (unit_number_x + unit_title_x) / 2,
        "unit_title_end": max(unit_title_x + 28, guide_start_x - 10),
        "guide_end": max(guide_end_x, guide_x + 26),
        "activity_end": max(activity_x + 36, textbook_start_x - 10),
        "textbook_end": max(textbook_end_x, textbook_x + 24),
        "hours_end": max(hours_x + 16, total_x - 10),
    }


def parse_activity_plan_hours(text: str) -> int | None:
    normalized = normalize_space(text)
    if not normalized:
        return None
    match = ACTIVITY_PLAN_HOURS_RE.fullmatch(normalized)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def split_activity_plan_textbook_and_hours(textbook_text: str, hours_text: str) -> tuple[str, str]:
    textbook = normalize_space(textbook_text)
    hours = normalize_space(hours_text)
    if hours:
        return textbook, hours

    parts = textbook.split()
    if len(parts) >= 2 and parse_page_ranges(" ".join(parts[:-1])) and parse_activity_plan_hours(parts[-1]) is not None:
        return normalize_space(" ".join(parts[:-1])), parts[-1]
    return textbook, hours


def is_activity_plan_domain_fragment(text: str) -> bool:
    normalized = normalize_space(text).replace(" ", "")
    return normalized in {"표현", "감상", "미적체험", "교과통합"}


def finalize_activity_plan_entry(entry: dict) -> dict | None:
    unit_title = normalize_activity_plan_title(" ".join(entry.get("title_parts", [])))
    if not unit_title or any(hint in unit_title for hint in ACTIVITY_PLAN_SKIP_TITLE_HINTS):
        return None

    activities: list[dict] = []
    for activity in entry.get("activities", []):
        title = normalize_activity_plan_title(" ".join(activity.get("title_parts", [])))
        if not title:
            continue
        if activities and activities[-1]["title"] == title:
            continue
        activities.append(
            {
                "title": title,
                "hours": activity.get("hours") or 1,
            }
        )

    if len(activities) < 2:
        return None

    return {
        "unit_title": unit_title,
        "unit_number": entry.get("unit_number"),
        "guide_ranges": entry.get("guide_ranges", []),
        "activities": activities,
    }


def parse_activity_plan_units_from_page(page) -> list[dict]:
    lines = extract_word_lines_from_page(page)
    if not lines or not is_activity_plan_candidate_page(lines):
        return []

    columns = detect_activity_plan_columns(lines)
    if not columns:
        return []

    parsed_rows: list[dict] = []

    for line in lines:
        if line["y"] <= columns["header_end_y"] + 3:
            continue

        full_text = line["text"]
        if not full_text or any(hint in full_text for hint in ACTIVITY_PLAN_SKIP_LINE_HINTS):
            continue

        column_words: dict[int, list[str]] = defaultdict(list)
        for x0, _, x1, _, word_text in line["words"]:
            center = (x0 + x1) / 2
            if center < columns["unit_number_end"]:
                column_words[0].append(word_text)
            elif center < columns["unit_title_end"]:
                column_words[1].append(word_text)
            elif center < columns["guide_end"]:
                column_words[2].append(word_text)
            elif center < columns["activity_end"]:
                column_words[3].append(word_text)
            elif center < columns["textbook_end"]:
                column_words[4].append(word_text)
            elif center < columns["hours_end"]:
                column_words[5].append(word_text)
            else:
                column_words[6].append(word_text)

        unit_prefix = normalize_space(" ".join(column_words[0]))
        unit_title = normalize_space(" ".join(column_words[1]))
        guide_text = normalize_space(" ".join(column_words[2]))
        activity_title = normalize_space(" ".join(column_words[3]))
        textbook_text = normalize_space(" ".join(column_words[4]))
        hours_text = normalize_space(" ".join(column_words[5]))
        textbook_text, hours_text = split_activity_plan_textbook_and_hours(textbook_text, hours_text)

        if not any((unit_prefix, unit_title, guide_text, activity_title, textbook_text, hours_text)):
            continue

        guide_ranges = parse_page_ranges(guide_text)
        unit_number = int(unit_prefix) if re.fullmatch(r"\d+", unit_prefix) else None
        project_prefix = unit_prefix if unit_prefix in ACTIVITY_PLAN_PROJECT_PARTS else ""
        title_fragments: list[str] = []
        if project_prefix:
            title_fragments.append(project_prefix)
        guide_text_without_ranges = normalize_space(re.sub(r"\d{1,3}\s*[~-]\s*\d{1,3}", " ", guide_text))
        combined_fragment = normalize_space(
            " ".join(
                part
                for part in (
                    unit_title,
                    guide_text if not guide_ranges else guide_text_without_ranges,
                )
                if part
            )
        )
        if not is_activity_plan_domain_fragment(combined_fragment):
            if unit_title:
                title_fragments.append(unit_title)
            if guide_text and not guide_ranges and not is_activity_plan_domain_fragment(guide_text):
                title_fragments.append(guide_text)
            elif guide_text_without_ranges and not is_activity_plan_domain_fragment(guide_text_without_ranges):
                title_fragments.append(guide_text_without_ranges)
        candidate_title = normalize_activity_plan_title(" ".join(title_fragments))
        if guide_ranges and candidate_title and any(hint in candidate_title for hint in ACTIVITY_PLAN_SKIP_TITLE_HINTS):
            continue

        hours = parse_activity_plan_hours(hours_text)
        activity_payload = None
        if activity_title:
            activity_payload = {
                "title_parts": [activity_title],
                "hours": hours,
            }
        parsed_rows.append(
            {
                "y": line["y"],
                "unit_number": unit_number,
                "title_fragments": title_fragments,
                "guide_ranges": guide_ranges,
                "activity": activity_payload,
            }
        )

    entries: list[dict] = []
    index = 0
    while index < len(parsed_rows):
        row = parsed_rows[index]
        starts_unit = bool(row["guide_ranges"])
        if not starts_unit:
            index += 1
            continue

        title_parts: list[str] = []
        activities: list[dict] = []
        lead_rows: list[dict] = []
        previous_index = index - 1
        while previous_index >= 0:
            previous_row = parsed_rows[previous_index]
            if previous_row["guide_ranges"]:
                break
            if row["y"] - previous_row["y"] > 20:
                break
            lead_rows.append(previous_row)
            previous_index -= 1
        lead_rows.reverse()

        for lead_row in lead_rows:
            title_parts.extend(lead_row["title_fragments"])
            if lead_row["activity"]:
                activities.append(
                    {
                        "title_parts": list(lead_row["activity"]["title_parts"]),
                        "hours": lead_row["activity"].get("hours"),
                    }
                )

        title_parts.extend(row["title_fragments"])
        if row["activity"]:
            activities.append(
                {
                    "title_parts": list(row["activity"]["title_parts"]),
                    "hours": row["activity"].get("hours"),
                }
            )

        next_index = index + 1
        while next_index < len(parsed_rows):
            next_row = parsed_rows[next_index]
            next_starts_unit = bool(next_row["guide_ranges"])
            upcoming_start = any(
                parsed_rows[probe_index]["guide_ranges"]
                for probe_index in range(next_index + 1, min(len(parsed_rows), next_index + 3))
            )
            if next_starts_unit:
                break
            if upcoming_start and (next_row["title_fragments"] or next_row["activity"]) and next_row["y"] - row["y"] > 20:
                break

            if next_row["title_fragments"]:
                if (
                    next_row["title_fragments"][0] in ACTIVITY_PLAN_PROJECT_PARTS
                    and title_parts
                    and title_parts[0] in ACTIVITY_PLAN_PROJECT_PARTS
                ):
                    title_parts[0] = normalize_activity_plan_title(title_parts[0] + next_row["title_fragments"][0])
                    title_parts.extend(next_row["title_fragments"][1:])
                else:
                    title_parts.extend(next_row["title_fragments"])
            if next_row["activity"]:
                activities.append(
                    {
                        "title_parts": list(next_row["activity"]["title_parts"]),
                        "hours": next_row["activity"].get("hours"),
                    }
                )
            next_index += 1

        entry = finalize_activity_plan_entry(
            {
                "unit_number": row["unit_number"],
                "title_parts": title_parts,
                "guide_ranges": row["guide_ranges"],
                "activities": activities,
            }
        )
        if entry:
            entries.append(entry)

        index = next_index

    return entries


def extract_activity_plan_units(pdf_doc, scan_pages: int = 80) -> list[dict]:
    total_pages = len(pdf_doc.pages)
    limit = min(scan_pages, total_pages)
    entries: list[dict] = []
    seen: set[tuple[str, tuple[str, ...]]] = set()

    for page_number in range(1, limit + 1):
        lines = extract_page_text(pdf_doc.pages[page_number - 1]).splitlines()
        preview = " ".join(normalize_space(line) for line in lines[:15] if normalize_space(line))
        if not all(marker in preview for marker in ACTIVITY_PLAN_HEADER_MARKERS[:3]):
            continue
        for entry in parse_activity_plan_units_from_page(pdf_doc.pages[page_number - 1]):
            key = (
                entry["unit_title"],
                tuple(activity["title"] for activity in entry["activities"]),
            )
            if key in seen:
                continue
            seen.add(key)
            entries.append(entry)

    return entries


def score_activity_plan_unit_match(parent_title: str, plan_unit_title: str) -> int:
    parent_tokens = entry_search_tokens(parent_title)
    plan_title = normalize_activity_plan_title(plan_unit_title)
    if not parent_tokens or not plan_title:
        return 0

    score = 0
    for index, token in enumerate(parent_tokens):
        if token in plan_title:
            score += 6 if index == 0 else 4

    stripped_parent = normalize_activity_plan_title(re.sub(r"^\d+\.\s*", "", parent_title))
    if stripped_parent and stripped_parent == plan_title:
        score += 10
    return score


def match_activity_plan_units_to_parents(parent_groups: list[dict], plan_units: list[dict]) -> dict[tuple[int, int, str], dict]:
    assignments: dict[tuple[int, int, str], dict] = {}
    if not parent_groups or not plan_units:
        return assignments

    used_indexes: set[int] = set()
    cursor = 0

    for parent_group in parent_groups:
        parent_title = normalize_space(parent_group.get("source_title") or parent_group["title"])
        best_index: int | None = None
        best_score = 0

        for index in range(cursor, len(plan_units)):
            if index in used_indexes:
                continue
            score = score_activity_plan_unit_match(parent_title, plan_units[index]["unit_title"])
            score -= min(4, max(0, index - cursor))
            if score > best_score:
                best_score = score
                best_index = index
            if best_score >= 16 and index - cursor >= 2:
                break

        if best_index is None:
            for index, plan_unit in enumerate(plan_units):
                if index in used_indexes:
                    continue
                score = score_activity_plan_unit_match(parent_title, plan_unit["unit_title"])
                if score > best_score:
                    best_score = score
                    best_index = index

        if best_index is None or best_score < 10:
            continue

        used_indexes.add(best_index)
        cursor = best_index + 1
        key = (
            parent_group["start_page"],
            parent_group["end_page"],
            parent_title,
        )
        assignments[key] = plan_units[best_index]

    return assignments


def split_parent_range_by_weights(start_page: int, end_page: int, weights: list[int]) -> list[tuple[int, int]]:
    total_pages = end_page - start_page + 1
    if total_pages <= 0 or not weights:
        return []

    safe_weights = [max(1, int(weight or 1)) for weight in weights]
    if total_pages < len(safe_weights):
        return []

    ranges: list[tuple[int, int]] = []
    cumulative_weight = 0
    previous_end = start_page - 1
    total_weight = sum(safe_weights)

    for index, weight in enumerate(safe_weights):
        if index == len(safe_weights) - 1:
            current_end = end_page
        else:
            cumulative_weight += weight
            target_size = round(total_pages * cumulative_weight / total_weight)
            remaining_groups = len(safe_weights) - index - 1
            min_current_end = previous_end + 1
            max_current_end = end_page - remaining_groups
            current_end = max(min_current_end, min(max_current_end, start_page + target_size - 1))

        current_start = previous_end + 1
        ranges.append((current_start, current_end))
        previous_end = current_end

    return ranges


def detect_top_art_activity_marker(page) -> tuple[int | None, bool]:
    try:
        lines = extract_word_lines_from_page(page)
    except Exception:
        return None, False

    top_lines = [line["text"] for line in lines if line["y"] <= 70][:6]
    if not top_lines:
        return None, False

    top_text = normalize_space(" ".join(top_lines))
    if "활동 1 + 마무리" in top_text or "활동1 + 마무리" in top_text:
        return 1, True
    if "활동 2 + 마무리" in top_text or "활동2 + 마무리" in top_text:
        return 2, True
    if "활동 1" in top_text or "활동1" in top_text:
        return 1, "마무리" in top_text
    if "활동 2" in top_text or "활동2" in top_text:
        return 2, "마무리" in top_text
    return None, False


def find_activity_plan_boundary_page(pdf_doc, parent_group: dict, activity_title: str) -> int | None:
    tokens = entry_search_tokens(activity_title)
    if not tokens:
        return None

    parent_start = parent_group["start_page"]
    parent_end = parent_group["end_page"]
    best_page: int | None = None
    best_score = 0
    exact_pair_pages: list[int] = []

    for page_number in range(parent_start + 1, parent_end + 1):
        page = pdf_doc.pages[page_number - 1]
        lines = [
            normalize_space(line)
            for line in extract_page_text(page).splitlines()
            if normalize_space(line)
        ]
        if not lines:
            continue

        preview_lines = lines[:24]
        preview_text = " ".join(preview_lines)
        score = 0
        current_marker, current_has_summary = detect_top_art_activity_marker(page)

        if current_marker == 2 and current_has_summary:
            score += 12
        elif current_marker == 2:
            score += 7

        if page_number > parent_start:
            previous_marker, previous_has_summary = detect_top_art_activity_marker(pdf_doc.pages[page_number - 2])
            if previous_marker == 1 and previous_has_summary and current_marker == 2:
                if current_has_summary:
                    exact_pair_pages.append(page_number)
                score += 10
            elif previous_marker == 1 and current_marker == 2:
                score += 6

        token_hits = sum(1 for token in tokens[:3] if token in preview_text)
        if current_marker == 2:
            if token_hits >= 2:
                score += 8
            elif token_hits == 1:
                score += 4

            if token_hits and any(marker in preview_text for marker in ("교수 학습", "교수·학습", "차시", "학습 주제", "교과서")):
                score += 3

        if score > best_score:
            best_score = score
            best_page = page_number

    if exact_pair_pages:
        return exact_pair_pages[0]
    if best_score >= 10:
        return best_page
    return None


def build_groups_from_activity_plan_entry(pdf_doc, parent_group: dict, plan_unit: dict) -> list[dict]:
    activities = plan_unit.get("activities", [])
    if len(activities) < 2:
        return []

    page_ranges: list[tuple[int, int]] = []
    if len(activities) == 2:
        boundary_page = find_activity_plan_boundary_page(pdf_doc, parent_group, activities[1]["title"])
        if boundary_page is not None and parent_group["start_page"] < boundary_page <= parent_group["end_page"]:
            page_ranges = [
                (parent_group["start_page"], boundary_page - 1),
                (boundary_page, parent_group["end_page"]),
            ]

    if not page_ranges:
        page_ranges = split_parent_range_by_weights(
            parent_group["start_page"],
            parent_group["end_page"],
            [activity.get("hours") or 1 for activity in activities],
        )
    if len(page_ranges) != len(activities):
        return []

    parent_title = normalize_space(parent_group.get("source_title") or parent_group["title"])
    groups: list[dict] = []
    for (start_page, end_page), activity in zip(page_ranges, activities):
        title = normalize_activity_plan_title(activity["title"]) or parent_title
        groups.append(
            {
                "title": shorten_title(title),
                "source_title": title,
                "start_page": start_page,
                "end_page": end_page,
                "row_evidence": 1,
                "page_ranges_raw": [(start_page, end_page)],
                "method": "activity_plan",
                "context": list(parent_group.get("context", [])),
                "detected_level": "detail",
                "parent_unit_title": parent_title,
                "hours": activity.get("hours") or 1,
            }
        )

    return groups


def is_music_plan_candidate_page(lines: list[dict]) -> bool:
    preview = " ".join(line["text"] for line in lines[:10])
    return all(marker in preview for marker in MUSIC_PLAN_HEADER_MARKERS)


def detect_music_plan_columns(lines: list[dict]) -> dict[str, float] | None:
    header_lines = [line for line in lines if line["y"] <= 90]
    if not header_lines:
        return None

    header_words = [word for line in header_lines for word in line["words"]]

    def first_x(*keywords: str, min_x: float = -1.0) -> float | None:
        xs = [
            word[0]
            for word in header_words
            if word[0] >= min_x and any(keyword in word[4] for keyword in keywords)
        ]
        return min(xs) if xs else None

    title_x = first_x("제재명")
    hours_x = first_x("차시", min_x=title_x or -1.0)
    content_x = first_x("교수", "학습", min_x=hours_x or -1.0)
    page_xs = sorted(word[0] for word in header_words if "쪽수" in word[4])
    if title_x is None or hours_x is None or content_x is None or len(page_xs) < 2:
        return None

    return {
        "title_x": title_x,
        "hours_x": hours_x,
        "content_x": content_x,
        "guide_x": page_xs[-1],
        "header_end_y": max(word[3] for word in header_words),
    }


def parse_music_plan_page(text: str) -> int | None:
    matches = MUSIC_PLAN_PAGE_RE.findall(normalize_space(text))
    if not matches:
        return None
    return int(matches[-1])


def finalize_music_plan_row(row: dict) -> dict | None:
    title = normalize_toc_title(" ".join(row.get("title_parts", [])))
    title = re.sub(r"^\d+\s*", "", title)
    if not title or any(hint in title for hint in MUSIC_PLAN_SKIP_TITLE_HINTS):
        return None

    printed_page = row.get("printed_page")
    if printed_page is None:
        return None

    return {
        "title": title,
        "printed_page": printed_page,
        "hours": row.get("hours") or 1,
        "source_page": row.get("source_page", 0),
    }


def parse_music_plan_rows_from_page(page) -> list[dict]:
    lines = extract_word_lines_from_page(page)
    if not lines or not is_music_plan_candidate_page(lines):
        return []

    columns = detect_music_plan_columns(lines)
    if not columns:
        return []

    rows: list[dict] = []
    current_row: dict | None = None

    for line in lines:
        if line["y"] <= columns["header_end_y"] + 3:
            continue

        title_words = [
            word[4]
            for word in line["words"]
            if 40 <= word[0] < columns["hours_x"] - 8
        ]
        hours_words = [
            word[4]
            for word in line["words"]
            if columns["hours_x"] - 8 <= word[0] < columns["content_x"] - 8
        ]
        guide_words = [word[4] for word in line["words"] if word[0] >= columns["guide_x"] - 6]

        title_text = normalize_toc_title(" ".join(title_words))
        hours = parse_activity_plan_hours(" ".join(hours_words))
        printed_page = parse_music_plan_page(" ".join(guide_words))

        if printed_page is not None and title_text:
            if current_row is not None:
                finalized = finalize_music_plan_row(current_row)
                if finalized is not None:
                    rows.append(finalized)
            current_row = {
                "title_parts": [title_text],
                "printed_page": printed_page,
                "hours": hours,
                "source_page": page.page_number,
            }
            continue

        if current_row is None or not title_text or printed_page is not None:
            continue

        if any(hint in title_text for hint in MUSIC_PLAN_SKIP_TITLE_HINTS):
            continue
        if title_text not in current_row["title_parts"] and len(title_text) <= 40:
            current_row["title_parts"].append(title_text)

    if current_row is not None:
        finalized = finalize_music_plan_row(current_row)
        if finalized is not None:
            rows.append(finalized)

    deduped: list[dict] = []
    seen: set[tuple[str, int]] = set()
    for row in rows:
        key = (row["title"], row["printed_page"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def infer_music_plan_page_offset(pdf_doc, parent_group: dict, rows: list[dict]) -> int:
    if not rows:
        return 0

    entries = [
        TocEntry(
            title=row["title"],
            printed_page=row["printed_page"],
            source_page=row["source_page"],
            context=tuple(parent_group.get("context", [])),
            level="subunit",
        )
        for row in rows
    ]

    candidate_offsets = {infer_toc_page_offset(pdf_doc, entries)}
    first_printed = rows[0]["printed_page"]
    for lead_pages in range(1, 6):
        candidate_offsets.add(parent_group["start_page"] + lead_pages - first_printed)

    best_offset = 0
    best_score = -10_000
    for offset in candidate_offsets:
        score = -abs(offset)
        mapped_pages = [row["printed_page"] + offset for row in rows]
        for row, mapped_page in zip(rows, mapped_pages):
            if parent_group["start_page"] <= mapped_page <= parent_group["end_page"]:
                score += 6
                if entry_matches_page(pdf_doc, mapped_page, entry_search_tokens(row["title"])):
                    score += 8
            else:
                score -= 20

        score += sum(1 for left, right in zip(mapped_pages, mapped_pages[1:]) if right > left) * 2
        if mapped_pages:
            lead_gap = mapped_pages[0] - parent_group["start_page"]
            if 2 <= lead_gap <= 5:
                score += 6
            elif 1 <= lead_gap <= 7:
                score += 3

        if score > best_score:
            best_score = score
            best_offset = offset

    return best_offset


def extract_music_unit_title(page, fallback_title: str) -> str:
    lines = [normalize_space(line) for line in extract_page_text(page).splitlines() if normalize_space(line)]
    for line in lines[:12]:
        if re.fullmatch(r"\d+", line):
            continue
        if any(marker in line for marker in MUSIC_PLAN_SKIP_TITLE_HINTS):
            continue
        if any(marker in line for marker in ("역량", "내용 체계", "성취기준", "교수·학습")):
            continue
        candidate = normalize_toc_title(line)
        if candidate:
            return candidate
    return normalize_space(fallback_title)

def normalize_music_unit_title(unit_title: str, unit_index: int) -> str:
    title = normalize_space(unit_title)
    if not title:
        return title
    if re.match(r"^\d+\s*[. ]?", title):
        return title
    if "프로젝트" in title:
        return title
    return f"{unit_index} {title}"





def build_groups_from_music_plan_entry(pdf_doc, parent_group: dict) -> list[dict]:
    parent_start = parent_group["start_page"]
    parent_end = parent_group["end_page"]
    parent_title = normalize_space(parent_group.get("source_title") or parent_group["title"])

    search_end = min(parent_end, parent_start + 4)
    for page_number in range(parent_start, search_end + 1):
        rows = parse_music_plan_rows_from_page(pdf_doc.pages[page_number - 1])
        if len(rows) < 2:
            continue

        offset = infer_music_plan_page_offset(pdf_doc, parent_group, rows)
        groups: list[dict] = []
        first_start_page = rows[0]["printed_page"] + offset
        if parent_start < first_start_page <= parent_end:
            intro_title = extract_music_unit_title(pdf_doc.pages[parent_start - 1], parent_title)
            groups.append(
                {
                    "title": shorten_title(intro_title),
                    "source_title": intro_title,
                    "start_page": parent_start,
                    "end_page": first_start_page - 1,
                    "row_evidence": 1,
                    "page_ranges_raw": [(parent_start, first_start_page - 1)],
                    "method": "music_plan_intro",
                    "context": list(parent_group.get("context", [])),
                    "detected_level": "detail",
                    "parent_unit_title": parent_title,
                    "hours": 1,
                }
            )

        for index, row in enumerate(rows):
            start_page = row["printed_page"] + offset
            if not (parent_start <= start_page <= parent_end):
                groups = []
                break

            next_start_page = (
                rows[index + 1]["printed_page"] + offset
                if index + 1 < len(rows)
                else parent_end + 1
            )
            end_page = min(parent_end, next_start_page - 1)
            if end_page < start_page:
                groups = []
                break

            title = normalize_toc_title(row["title"]) or parent_title
            groups.append(
                {
                    "title": shorten_title(title),
                    "source_title": title,
                    "start_page": start_page,
                    "end_page": end_page,
                    "row_evidence": 1,
                    "page_ranges_raw": [(row["printed_page"], row["printed_page"])],
                    "method": "music_plan",
                    "context": list(parent_group.get("context", [])),
                    "detected_level": "detail",
                    "parent_unit_title": parent_title,
                    "hours": row.get("hours") or 1,
                }
            )

        if len(groups) >= 2:
            return groups

    return []


def extract_music_plan_units(pdf_doc) -> list[dict]:
    total_pages = len(pdf_doc.pages)
    units: list[dict] = []
    seen_starts: set[int] = set()

    for page_number in range(2, total_pages + 1):
        rows = parse_music_plan_rows_from_page(pdf_doc.pages[page_number - 1])
        if len(rows) < 2:
            continue

        start_page = page_number - 1
        if start_page in seen_starts:
            continue

        unit_title = extract_music_unit_title(
            pdf_doc.pages[start_page - 1],
            rows[0]["title"],
        )
        seen_starts.add(start_page)
        units.append(
            {
                "title": unit_title,
                "start_page": start_page,
                "plan_page": page_number,
                "rows": rows,
            }
        )

    units.sort(key=lambda item: item["start_page"])
    for index, unit in enumerate(units, start=1):
        unit["title"] = normalize_music_unit_title(unit.get("title", ""), index)
        next_start = units[index]["start_page"] if index < len(units) else total_pages + 1
        unit["end_page"] = max(unit["start_page"], next_start - 1)
    return units


def build_groups_from_music_plan_pages(pdf_doc, split_level: str) -> list[dict]:
    music_units = extract_music_plan_units(pdf_doc)
    if len(music_units) < 2:
        return []

    groups: list[dict] = []
    first_start = music_units[0]["start_page"]
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
                "method": "music_plan_leading_section",
                "context": [],
                "detected_level": "section",
            }
        )

    if split_level == "unit":
        for offset_index, unit in enumerate(music_units, start=len(groups) + 1):
            unit_title = normalize_space(unit["title"])
            groups.append(
                {
                    "index": offset_index,
                    "title": shorten_title(unit_title),
                    "source_title": unit_title,
                    "start_page": unit["start_page"],
                    "end_page": unit["end_page"],
                    "row_evidence": 1,
                    "page_ranges_raw": [(unit["start_page"], unit["start_page"])],
                    "method": "music_plan_page",
                    "context": [],
                    "detected_level": "unit",
                    "parent_unit_title": unit_title,
                }
            )
        return groups

    for unit in music_units:
        unit_title = normalize_space(unit["title"])
        parent_group = {
            "title": unit_title,
            "source_title": unit_title,
            "start_page": unit["start_page"],
            "end_page": unit["end_page"],
            "context": [],
        }
        rows = unit["rows"]
        offset = infer_music_plan_page_offset(pdf_doc, parent_group, rows)
        unit_groups: list[dict] = []

        first_detail_start = rows[0]["printed_page"] + offset
        if unit["start_page"] < first_detail_start <= unit["end_page"]:
            unit_groups.append(
                {
                    "title": shorten_title(unit_title),
                    "source_title": unit_title,
                    "start_page": unit["start_page"],
                    "end_page": first_detail_start - 1,
                    "row_evidence": 1,
                    "page_ranges_raw": [(unit["start_page"], first_detail_start - 1)],
                    "method": "music_plan_intro",
                    "context": [],
                    "detected_level": "detail",
                    "parent_unit_title": unit_title,
                    "hours": 1,
                }
            )

        valid = True
        for index, row in enumerate(rows):
            start_page = row["printed_page"] + offset
            next_start = rows[index + 1]["printed_page"] + offset if index + 1 < len(rows) else unit["end_page"] + 1
            end_page = min(unit["end_page"], next_start - 1)
            if start_page < unit["start_page"] or start_page > unit["end_page"] or end_page < start_page:
                valid = False
                break

            title = normalize_toc_title(row["title"]) or unit_title
            unit_groups.append(
                {
                    "title": shorten_title(title),
                    "source_title": title,
                    "start_page": start_page,
                    "end_page": end_page,
                    "row_evidence": 1,
                    "page_ranges_raw": [(row["printed_page"], row["printed_page"])],
                    "method": "music_plan",
                    "context": [],
                    "detected_level": "detail",
                    "parent_unit_title": unit_title,
                    "hours": row.get("hours") or 1,
                }
            )

        if not valid or len(unit_groups) < 2:
            unit_groups = [
                {
                    "title": shorten_title(unit_title),
                    "source_title": unit_title,
                    "start_page": unit["start_page"],
                    "end_page": unit["end_page"],
                    "row_evidence": 1,
                    "page_ranges_raw": [(unit["start_page"], unit["start_page"])],
                    "method": "music_plan_page",
                    "context": [],
                    "detected_level": "detail",
                    "parent_unit_title": unit_title,
                }
            ]

        groups.extend(unit_groups)

    return renumber_groups(groups)


def is_parent_unit_group(group: dict) -> bool:
    return group.get("detected_level") in {"subunit", "project", "unit"}


def extract_text_window(pdf_doc, start_page: int, end_page: int, max_pages: int = 6) -> str:
    snippets: list[str] = []
    for page_no in range(start_page, min(end_page, start_page + max_pages - 1) + 1):
        snippets.append(extract_page_text(pdf_doc.pages[page_no - 1]))
    return "\n".join(snippets)


def group_looks_like_curriculum_unit(pdf_doc, group: dict) -> bool:
    title = normalize_space(group.get("source_title") or group["title"])
    if any(hint in title for hint in LOCAL_DETAIL_EXCLUDE_TITLE_HINTS):
        return False

    start_page = group["start_page"]
    end_page = group["end_page"]
    if start_page < 1 or end_page < start_page:
        return False

    first_page_text = extract_page_text(pdf_doc.pages[start_page - 1])
    window_text = extract_text_window(pdf_doc, start_page, min(end_page, start_page + 5))

    strong_hits = sum(1 for hint in UNIT_START_STRONG_HINTS if hint in window_text)
    support_hits = sum(1 for hint in UNIT_START_SUPPORT_HINTS if hint in window_text)

    if ("교육과정" in first_page_text and "핵심 아이디어" in window_text):
        return True
    if "단원의 개관" in window_text or "제재 개관" in window_text:
        return True
    if "단원 소개" in window_text and "단원 지도 계획" in window_text:
        return True
    if strong_hits >= 2 and support_hits >= 1:
        return True
    return False


def describe_gap_title(
    pdf_doc,
    parent_title: str,
    start_page: int,
    end_page: int,
    *,
    is_leading: bool,
    is_trailing: bool,
    index: int,
) -> str:
    text = extract_text_window(pdf_doc, start_page, end_page, max_pages=4)
    if "자료 출처" in text:
        return f"{parent_title} 자료 출처"
    if "단원 배경지식" in text or "참고 문헌" in text:
        return f"{parent_title} 배경지식 및 참고 자료"
    if "교수 · 학습 과정안" in text or "과정 중심 평가 예시" in text or "교과 역량 평가 계획" in text:
        return f"{parent_title} 지도 및 평가 자료"
    if "단원 소개" in text or "단원의 학습 목표" in text or "단원의 흐름" in text:
        return f"{parent_title} 단원 개관 및 자료"
    if is_leading:
        return f"{parent_title} 단원 자료"
    if is_trailing:
        return f"{parent_title} 마무리 자료"
    return f"{parent_title} 참고 자료 {index}"


def gap_has_distinct_section_signal(pdf_doc, start_page: int, end_page: int) -> bool:
    text = extract_text_window(pdf_doc, start_page, end_page, max_pages=4)
    distinct_hints = (
        "자료 출처",
        "단원 배경지식",
        "참고 문헌",
        "교수 · 학습 과정안",
        "과정 중심 평가 예시",
        "교과 역량 평가 계획",
        "단원 소개",
        "단원의 학습 목표",
        "단원의 흐름",
    )
    return any(hint in text for hint in distinct_hints)


def should_emit_gap_group(pdf_doc, start_page: int, end_page: int, *, is_leading: bool, is_trailing: bool) -> bool:
    gap_pages = end_page - start_page + 1
    if gap_pages <= 0:
        return False
    if gap_has_distinct_section_signal(pdf_doc, start_page, end_page):
        return True
    if is_leading:
        return gap_pages > MAX_ABSORBED_LEADING_GAP_PAGES
    if is_trailing:
        return gap_pages > MAX_ABSORBED_TRAILING_GAP_PAGES
    return gap_pages > MAX_ABSORBED_MIDDLE_GAP_PAGES


def absorb_gap_into_group(group: dict, start_page: int, end_page: int, *, prepend: bool) -> dict:
    if start_page > end_page:
        return group
    if prepend:
        group["start_page"] = min(group["start_page"], start_page)
    else:
        group["end_page"] = max(group["end_page"], end_page)
    group.setdefault("page_ranges_raw", []).append((start_page, end_page))
    return group


def normalize_groups_within_parent(pdf_doc, parent_group: dict, detail_groups: list[dict]) -> list[dict]:
    if not detail_groups:
        return []

    parent_start = parent_group["start_page"]
    parent_end = parent_group["end_page"]
    parent_title = parent_group.get("source_title") or parent_group["title"]

    normalized: list[dict] = []
    for group in sorted(detail_groups, key=lambda item: (item["start_page"], item["end_page"], item["title"])):
        if group["end_page"] < parent_start or group["start_page"] > parent_end:
            continue
        current = clone_group(group)
        current["start_page"] = max(parent_start, current["start_page"])
        current["end_page"] = min(parent_end, current["end_page"])
        current["parent_unit_title"] = parent_title
        normalized.append(current)

    if not normalized:
        return []

    normalized_groups: list[dict] = []
    cursor = parent_start
    filler_index = 1
    for group in normalized:
        if group["start_page"] > cursor:
            gap_start = cursor
            gap_end = group["start_page"] - 1
            if should_emit_gap_group(
                pdf_doc,
                gap_start,
                gap_end,
                is_leading=cursor == parent_start,
                is_trailing=False,
            ):
                filler_title = describe_gap_title(
                    pdf_doc,
                    parent_title,
                    gap_start,
                    gap_end,
                    is_leading=cursor == parent_start,
                    is_trailing=False,
                    index=filler_index,
                )
                normalized_groups.append(
                    {
                        "title": shorten_title(filler_title),
                        "source_title": filler_title,
                        "start_page": gap_start,
                        "end_page": gap_end,
                        "row_evidence": 0,
                        "page_ranges_raw": [(gap_start, gap_end)],
                        "method": "unit_gap",
                        "context": list(parent_group.get("context", [])),
                        "detected_level": "detail",
                        "parent_unit_title": parent_title,
                    }
                )
                filler_index += 1
            else:
                group = absorb_gap_into_group(group, gap_start, gap_end, prepend=True)

        if normalized_groups and normalized_groups[-1]["end_page"] >= group["start_page"]:
            group["start_page"] = normalized_groups[-1]["end_page"] + 1
        if group["start_page"] <= group["end_page"]:
            normalized_groups.append(group)
            cursor = group["end_page"] + 1

    if cursor <= parent_end:
        if should_emit_gap_group(
            pdf_doc,
            cursor,
            parent_end,
            is_leading=False,
            is_trailing=True,
        ):
            filler_title = describe_gap_title(
                pdf_doc,
                parent_title,
                cursor,
                parent_end,
                is_leading=False,
                is_trailing=True,
                index=filler_index,
            )
            normalized_groups.append(
                {
                    "title": shorten_title(filler_title),
                    "source_title": filler_title,
                    "start_page": cursor,
                    "end_page": parent_end,
                    "row_evidence": 0,
                    "page_ranges_raw": [(cursor, parent_end)],
                    "method": "unit_gap",
                    "context": list(parent_group.get("context", [])),
                    "detected_level": "detail",
                    "parent_unit_title": parent_title,
                }
            )
        elif normalized_groups:
            normalized_groups[-1] = absorb_gap_into_group(normalized_groups[-1], cursor, parent_end, prepend=False)

    return normalized_groups


def process_guide_line_matches_parent(line: str, parent_title: str) -> bool:
    normalized = normalize_space(line)
    if "단원명" not in normalized or "차시" not in normalized or "과정안" not in normalized:
        return False
    tokens = entry_search_tokens(parent_title)
    if len(tokens) >= 2:
        return all(token in normalized for token in tokens[:2])
    return bool(tokens and tokens[0] in normalized)


def extract_lead_in_detail_title(lines: list[str], fallback_title: str) -> str:
    bullet_titles: list[str] = []
    seen: set[str] = set()
    for line in lines[:20]:
        if not line.startswith("•"):
            continue
        candidate = shorten_title(normalize_toc_title(line.replace("•", " ")))
        if not candidate or len(candidate) > 40 or candidate in seen:
            continue
        seen.add(candidate)
        bullet_titles.append(candidate)
        if len(bullet_titles) >= 2:
            break

    if bullet_titles:
        return shorten_title(" / ".join(bullet_titles))
    return shorten_title(fallback_title)


def extract_process_guide_title(lines: list[str], fallback_title: str) -> str:
    for line in lines[:15]:
        if "학습 주제" not in line:
            continue
        candidate = normalize_space(line.split("학습 주제", 1)[1])
        candidate = normalize_toc_title(candidate)
        if candidate:
            return shorten_title(candidate)
    return shorten_title(fallback_title)


def build_groups_from_page_header_patterns(pdf_doc, parent_group: dict) -> list[dict]:
    parent_start = parent_group["start_page"]
    parent_end = parent_group["end_page"]
    parent_title = normalize_space(parent_group.get("source_title") or parent_group["title"])
    process_starts: list[tuple[int, str]] = []

    for page_number in range(parent_start, parent_end + 1):
        lines = [
            normalize_space(line)
            for line in extract_page_text(pdf_doc.pages[page_number - 1]).splitlines()
            if normalize_space(line)
        ]
        for line in lines[:12]:
            if process_guide_line_matches_parent(line, parent_title):
                process_starts.append((page_number, extract_process_guide_title(lines, parent_title)))
                break

    if not process_starts:
        return []

    groups: list[dict] = []
    first_process_start = process_starts[0][0]
    if parent_start < first_process_start:
        start_lines = [
            normalize_space(line)
            for line in extract_page_text(pdf_doc.pages[parent_start - 1]).splitlines()
            if normalize_space(line)
        ]
        intro_title = extract_lead_in_detail_title(start_lines, parent_title)
        groups.append(
            {
                "title": intro_title,
                "source_title": intro_title,
                "start_page": parent_start,
                "end_page": first_process_start - 1,
                "row_evidence": 1,
                "page_ranges_raw": [(parent_start, first_process_start - 1)],
                "method": "page_header",
                "context": list(parent_group.get("context", [])),
                "detected_level": "detail",
            }
        )

    for index, (start_page, title) in enumerate(process_starts):
        next_start = process_starts[index + 1][0] if index + 1 < len(process_starts) else parent_end + 1
        groups.append(
            {
                "title": title,
                "source_title": title,
                "start_page": start_page,
                "end_page": next_start - 1,
                "row_evidence": 1,
                "page_ranges_raw": [(start_page, next_start - 1)],
                "method": "page_header",
                "context": list(parent_group.get("context", [])),
                "detected_level": "detail",
            }
        )

    return groups if len(groups) >= 2 else []


def build_local_detail_groups_for_parent(
    pdf_doc,
    parent_group: dict,
    page_offset: int,
    z_col: int | None,
) -> list[dict]:
    if not group_looks_like_curriculum_unit(pdf_doc, parent_group):
        return []

    search_start = parent_group["start_page"]
    search_end = min(parent_group["end_page"], parent_group["start_page"] + 12)
    local_scan_pages = max(0, search_end - search_start + 1)
    if local_scan_pages < 2:
        return []

    music_plan_groups = build_groups_from_music_plan_entry(pdf_doc, parent_group)
    if len(music_plan_groups) >= 2:
        return music_plan_groups

    plan_groups, _ = build_groups_from_plan_tables(
        pdf_doc,
        scan_pages=local_scan_pages,
        page_offset=page_offset,
        z_col=z_col,
        start_page=search_start,
        end_page=search_end,
    )
    if len(plan_groups) >= 2:
        return normalize_groups_within_parent(pdf_doc, parent_group, plan_groups)

    plan_text_groups, _ = build_groups_from_plan_text(
        pdf_doc,
        scan_pages=local_scan_pages,
        page_offset=page_offset,
        preferred_first_start=search_start,
        start_page=search_start,
        end_page=search_end,
    )
    if len(plan_text_groups) >= 2:
        return normalize_groups_within_parent(pdf_doc, parent_group, plan_text_groups)

    page_header_groups = build_groups_from_page_header_patterns(pdf_doc, parent_group)
    if len(page_header_groups) >= 2:
        return normalize_groups_within_parent(pdf_doc, parent_group, page_header_groups)

    return []


def refine_detail_groups_from_parent_units(
    pdf_doc,
    groups: list[dict],
    page_offset: int,
    z_col: int | None,
) -> list[dict]:
    refined_groups: list[dict] = []
    replaced_any = False
    parent_candidates = [
        group
        for group in groups
        if is_parent_unit_group(group)
        and group["end_page"] - group["start_page"] + 1 >= 6
        and (group.get("detected_level") == "project" or group_looks_like_curriculum_unit(pdf_doc, group))
    ]
    activity_plan_assignments = match_activity_plan_units_to_parents(
        parent_candidates,
        extract_activity_plan_units(pdf_doc),
    )

    for group in groups:
        if not is_parent_unit_group(group) or group["end_page"] - group["start_page"] + 1 < 6:
            refined_groups.append(clone_group(group))
            continue

        local_groups: list[dict] = []
        if group.get("detected_level") == "project" or group_looks_like_curriculum_unit(pdf_doc, group):
            group_key = (
                group["start_page"],
                group["end_page"],
                normalize_space(group.get("source_title") or group["title"]),
            )
            plan_unit = activity_plan_assignments.get(group_key)
            if plan_unit:
                local_groups = build_groups_from_activity_plan_entry(pdf_doc, group, plan_unit)

        if not local_groups:
            local_groups = build_local_detail_groups_for_parent(
                pdf_doc,
                parent_group=group,
                page_offset=page_offset,
                z_col=z_col,
            )
        if local_groups:
            refined_groups.extend(local_groups)
            replaced_any = True
        else:
            refined_groups.append(clone_group(group))

    if not replaced_any:
        return []
    return renumber_groups(refined_groups)


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

    if strategy_used in {"toc", "toc_detail"}:
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


def content_groups_for_scoring(groups: list[dict]) -> list[dict]:
    content_groups = [group for group in groups if group.get("detected_level") != "section"]
    return content_groups or [clone_group(group) for group in groups]


def count_group_overlaps(groups: list[dict]) -> int:
    overlaps = 0
    previous_end = 0
    for group in sorted(groups, key=lambda item: (item["start_page"], item["end_page"], item["title"])):
        if group["start_page"] <= previous_end:
            overlaps += 1
        previous_end = max(previous_end, group["end_page"])
    return overlaps


def merged_group_coverage_pages(groups: list[dict]) -> int:
    intervals = sorted((group["start_page"], group["end_page"]) for group in groups if group["end_page"] >= group["start_page"])
    if not intervals:
        return 0

    merged_total = 0
    current_start, current_end = intervals[0]
    for start_page, end_page in intervals[1:]:
        if start_page <= current_end + 1:
            current_end = max(current_end, end_page)
            continue
        merged_total += current_end - current_start + 1
        current_start, current_end = start_page, end_page

    merged_total += current_end - current_start + 1
    return merged_total


def candidate_groups_look_reasonable(
    groups: list[dict],
    strategy_used: str,
    split_level: str,
    total_pages: int,
) -> bool:
    content_groups = content_groups_for_scoring(groups)
    if not content_groups:
        return False

    if any(group["start_page"] < 1 or group["end_page"] < group["start_page"] for group in content_groups):
        return False

    suspicious_titles = sum(1 for group in content_groups if is_suspicious_group_title(group["title"]))
    single_page_groups = sum(1 for group in content_groups if group["start_page"] == group["end_page"])
    overlap_count = count_group_overlaps(content_groups)
    coverage_pages = merged_group_coverage_pages(content_groups)

    if suspicious_titles >= max(2, len(content_groups) // 2):
        return False
    if len(content_groups) >= 6 and single_page_groups > len(content_groups) // 2:
        return False
    if overlap_count > max(1, len(content_groups) // 5):
        return False
    if total_pages > 0 and coverage_pages == 0:
        return False
    if split_level == "detail" and len(content_groups) == 1 and strategy_used != "overview_page":
        return False
    return True


def score_candidate_groups(
    groups: list[dict],
    strategy_used: str,
    split_level: str,
    total_pages: int,
) -> int:
    if not candidate_groups_look_reasonable(groups, strategy_used, split_level, total_pages):
        return -10_000

    content_groups = content_groups_for_scoring(groups)
    suspicious_titles = sum(1 for group in content_groups if is_suspicious_group_title(group["title"]))
    single_page_groups = sum(1 for group in content_groups if group["start_page"] == group["end_page"])
    overlap_count = count_group_overlaps(content_groups)
    coverage_pages = merged_group_coverage_pages(content_groups)
    unit_gap_count = sum(1 for group in content_groups if group.get("method") == "unit_gap")
    detail_source_count = sum(
        1
        for group in content_groups
        if group.get("method") in {"plan_table", "plan_text", "activity_plan", "music_plan"}
    )

    score = len(content_groups) * 4
    score += min(coverage_pages, total_pages)
    score -= suspicious_titles * 12
    score -= single_page_groups * 3
    score -= overlap_count * 8
    score -= unit_gap_count * 2

    if strategy_used == "toc_detail":
        score += 24
    elif strategy_used == "toc":
        score += 16
    elif strategy_used == "overview_detail":
        score += 18
    elif strategy_used == "overview_page":
        score += 14 if split_level == "unit" else 8
    elif strategy_used == "plan_table":
        score += 12
    elif strategy_used == "plan_text":
        score += 8

    if split_level == "detail":
        score += detail_source_count * 2
        if strategy_used == "toc_detail":
            score += 8
    else:
        unit_like_count = sum(1 for group in content_groups if group.get("detected_level") in {"subunit", "project", "unit"})
        score += unit_like_count * 3

    if len(content_groups) == 1:
        score -= 10 if split_level == "detail" else 4

    return score


def pick_best_candidate(
    candidates: list[tuple[list[dict], list[dict], str, int]],
    *,
    split_level: str,
    total_pages: int,
) -> tuple[list[dict], list[dict], str, int]:
    if not candidates:
        return [], [], "", 0

    scored_candidates = sorted(
        (
            (
                score_candidate_groups(
                    apply_split_level(groups, strategy_used=strategy_used, split_level=split_level),
                    strategy_used,
                    split_level,
                    total_pages,
                ),
                groups,
                sections,
                strategy_used,
                auto_offset,
                len(apply_split_level(groups, strategy_used=strategy_used, split_level=split_level)),
            )
            for groups, sections, strategy_used, auto_offset in candidates
            if groups
        ),
        key=lambda item: (item[0], item[5]),
        reverse=True,
    )
    if scored_candidates and scored_candidates[0][0] > -10_000:
        _, groups, sections, strategy_used, auto_offset, _ = scored_candidates[0]
        return groups, sections, strategy_used, auto_offset

    fallback_groups, fallback_sections, fallback_strategy, fallback_offset = candidates[0]
    return fallback_groups, fallback_sections, fallback_strategy, fallback_offset


def choose_groups(
    pdf_doc,
    scan_pages: int,
    page_offset: int,
    z_col: int | None,
    strategy: str,
    split_level: str,
) -> tuple[list[dict], list[dict], str, int]:
    total_pages = len(pdf_doc.pages)
    music_groups = build_groups_from_music_plan_pages(pdf_doc, split_level)
    if music_groups and strategy in {"auto", "overview"}:
        return music_groups, [], "music_plan_page", 0

    toc_groups: list[dict] = []
    toc_sections: list[dict] = []
    auto_offset = 0
    toc_detail_candidate: tuple[list[dict], list[dict], str, int] | None = None
    overview_detail_candidate: tuple[list[dict], list[dict], str, int] | None = None

    if strategy in {"auto", "toc"}:
        toc_entries = find_toc_entries(pdf_doc, scan_pages=scan_pages)
        toc_groups, toc_sections, auto_offset = build_groups_from_toc_entries(pdf_doc, toc_entries, page_offset)
        if toc_groups and toc_groups_look_reasonable(toc_groups):
            if split_level == "detail":
                refined_toc_groups = refine_detail_groups_from_parent_units(
                    pdf_doc,
                    groups=toc_groups,
                    page_offset=page_offset + auto_offset,
                    z_col=z_col,
                )
                if refined_toc_groups:
                    if strategy == "toc":
                        return refined_toc_groups, toc_sections, "toc_detail", auto_offset
                    toc_detail_candidate = (refined_toc_groups, toc_sections, "toc_detail", auto_offset)
                else:
                    toc_detail_candidate = None
            else:
                toc_detail_candidate = None

            if strategy == "toc":
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
        if split_level == "detail" and overview_groups:
            overview_unit_groups = build_unit_groups_from_overview(overview_groups)
            refined_overview_groups = refine_detail_groups_from_parent_units(
                pdf_doc,
                groups=overview_unit_groups,
                page_offset=page_offset,
                z_col=z_col,
            )
            if refined_overview_groups and any(
                group.get("method") in {"music_plan", "music_plan_intro"}
                for group in refined_overview_groups
            ):
                return refined_overview_groups, [], "overview_detail", 0
        if overview_groups:
            return overview_groups, [], "overview_page", 0
        return [], [], "overview", 0

    overview_groups = build_groups_from_overview_pages(pdf_doc)
    preferred_first_start = None
    content_overview_groups = [
        group for group in overview_groups if group.get("detected_level") != "section"
    ]
    if len(content_overview_groups) == 1:
        preferred_first_start = content_overview_groups[0]["start_page"]
    if split_level == "detail" and overview_groups:
        overview_unit_groups = build_unit_groups_from_overview(overview_groups)
        refined_overview_groups = refine_detail_groups_from_parent_units(
            pdf_doc,
            groups=overview_unit_groups,
            page_offset=page_offset,
            z_col=z_col,
        )
        if refined_overview_groups and any(
            group.get("method") in {"music_plan", "music_plan_intro"}
            for group in refined_overview_groups
        ):
            overview_detail_candidate = (refined_overview_groups, [], "overview_detail", 0)

    plan_groups, plan_auto_offset = build_groups_from_plan_tables(
        pdf_doc,
        scan_pages=scan_pages,
        page_offset=page_offset,
        z_col=z_col,
    )
    plan_text_groups, plan_text_auto_offset = build_groups_from_plan_text(
        pdf_doc,
        scan_pages=scan_pages,
        page_offset=page_offset,
        preferred_first_start=preferred_first_start,
    )

    if strategy != "auto":
        if split_level == "detail":
            if overview_detail_candidate is not None:
                return overview_detail_candidate
            if plan_groups:
                return plan_groups, [], "plan_table", plan_auto_offset
            if plan_text_groups:
                return plan_text_groups, [], "plan_text", plan_text_auto_offset
            if overview_groups:
                return overview_groups, [], "overview_page", 0
        else:
            if overview_groups:
                return overview_groups, [], "overview_page", 0
            if plan_groups:
                return plan_groups, [], "plan_table", plan_auto_offset
            if plan_text_groups:
                return plan_text_groups, [], "plan_text", plan_text_auto_offset
        return [], [], strategy, 0

    candidates: list[tuple[list[dict], list[dict], str, int]] = []
    if toc_groups and toc_groups_look_reasonable(toc_groups):
        candidates.append((toc_groups, toc_sections, "toc", auto_offset))
    if toc_detail_candidate is not None:
        candidates.append(toc_detail_candidate)
    if overview_detail_candidate is not None:
        candidates.append(overview_detail_candidate)
    if overview_groups:
        candidates.append((overview_groups, [], "overview_page", 0))
    if plan_groups:
        candidates.append((plan_groups, [], "plan_table", plan_auto_offset))
    if plan_text_groups:
        candidates.append((plan_text_groups, [], "plan_text", plan_text_auto_offset))

    best_groups, best_sections, best_strategy, best_offset = pick_best_candidate(
        candidates,
        split_level=split_level,
        total_pages=total_pages,
    )
    if best_groups:
        return best_groups, best_sections, best_strategy, best_offset

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
    existing_run_dir: str = "reuse",
    run_dir: str | Path | None = None,
    use_cache: bool = False,
) -> list[dict]:
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_file}")

    if not dry_run and not save:
        dry_run = True

    output_root = Path(out_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    if run_dir is None:
        run_dir_path = resolve_run_directory(
            output_root,
            pdf_file,
            existing_run_dir=existing_run_dir,
            create=True,
        )
    else:
        run_dir_path = Path(run_dir)
        run_dir_path.mkdir(parents=True, exist_ok=True)
    run_dir = run_dir_path
    groups_path = run_dir / "groups.json"

    # --- Cache Check ---
    cache_dir = output_root / ".cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    md5 = hashlib.md5()
    with pdf_file.open("rb") as f:
        # Read the first 4MB to hash quickly but uniquely
        md5.update(f.read(4 * 1024 * 1024))
    file_hash = md5.hexdigest()
    
    cache_key = f"{CACHE_SCHEMA_VERSION}_{file_hash}_{scan_pages}_{page_offset}_{z_col}_{strategy}_{split_level}.json"
    cache_file = cache_dir / cache_key
    
    cache_used = False
    if use_cache and cache_file.exists():
        with cache_file.open("r", encoding="utf-8") as f:
            cdata = json.load(f)
            detected_groups = cdata["detected_groups"]
            sections = cdata["sections"]
            strategy_used = cdata["strategy_used"]
            auto_offset = cdata["auto_offset"]
            total_pages = cdata["total_pages"]
            cache_used = True
            print("[INFO] Cache Hit: PDF structural data loaded instantly from cache.")
    else:
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
            
        if use_cache:
            with cache_file.open("w", encoding="utf-8") as f:
                json.dump({
                    "detected_groups": detected_groups,
                    "sections": sections,
                    "strategy_used": strategy_used,
                    "auto_offset": auto_offset,
                    "total_pages": total_pages
                }, f, ensure_ascii=False)
    # --- End Cache Check ---

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
                "cache_enabled": use_cache,
                "cache_used": cache_used,
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
            pdf_name=pdf_file.name,
            parent_title=group.get("parent_unit_title"),
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
        "--existing-run-dir",
        default="reuse",
        choices=("reuse", "replace", "suffix"),
        help="When the PDF-named output folder already exists: reuse it, replace it, or create a suffixed folder",
    )
    parser.add_argument(
        "--use-cache",
        action="store_true",
        help="Reuse previously saved structural analysis from output/.cache when available",
    )
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
        existing_run_dir=args.existing_run_dir,
        use_cache=args.use_cache,
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
