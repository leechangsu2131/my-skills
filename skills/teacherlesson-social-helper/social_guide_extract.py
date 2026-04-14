from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List, Optional

try:
    import fitz  # PyMuPDF

    FITZ_AVAILABLE = True
except ImportError:
    fitz = None
    FITZ_AVAILABLE = False


PLAN_PAGE_MARKERS = (
    "단원의 지도 계획",
    "주제의 지도 계획",
    "성취 기준",
    "성취 기준별 성취 수준",
    "영역별 성취 수준",
    "큐알 코드 목록",
)
PLAN_LAYOUT_MARKERS = (
    "차시명",
    "주요 학습 내용",
    "학생 활동",
    "쪽수",
)
LESSON_START_MARKERS = (
    "교수학습 과정",
    "학습 목표",
    "차시 안내",
    "수업 기법 및 전략",
    "학습 흐름",
)
STRONG_LESSON_START_MARKERS = (
    "교수학습 과정",
    "학습 목표",
    "차시 안내",
)
LESSON_SUPPORT_MARKERS = (
    "학습 안내",
    "학습 문제 확인하기",
    "도입",
    "전개",
    "정리",
)
REFERENCE_PAGE_MARKERS = (
    "활동지",
    "풀이",
    "과정 중심 평가",
)


def normalize_space(text: str) -> str:
    return " ".join((text or "").split())


def normalize_search_text(text: str) -> str:
    return re.sub(r"[^\w]", "", normalize_space(text)).lower()


def parse_exact_title(exact_title: str) -> tuple[str, str]:
    match = re.search(r"\[(.*?)\]\s*(.*)", exact_title or "")
    if match:
        lesson_label = normalize_space(match.group(1))
        topic = normalize_space(match.group(2))
        return lesson_label, topic
    return "", normalize_space(exact_title)


def strip_textbook_pages(topic: str) -> str:
    stripped = re.sub(r"\([^)]*p\)", "", topic or "", flags=re.IGNORECASE)
    return normalize_space(stripped)


def extract_textbook_pages(exact_title: str) -> str:
    match = re.search(r"\((?:[^0-9)]*?)?(\d+\s*~\s*\d+)\s*p\)", exact_title or "", flags=re.IGNORECASE)
    if not match:
        return ""
    return normalize_search_text(f"교과서 {match.group(1)}쪽")


def compact_lesson_text(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def parse_lesson_range(lesson_label: str) -> Optional[tuple[int, int]]:
    compact_label = compact_lesson_text(lesson_label)
    match = re.search(r"(\d+)(?:~(\d+))?", compact_label)
    if not match:
        return None

    start = int(match.group(1))
    end = int(match.group(2) or match.group(1))
    return start, end


def build_next_lesson_pattern(lesson_label: str) -> Optional[re.Pattern[str]]:
    lesson_range = parse_lesson_range(lesson_label)
    if not lesson_range:
        return None

    _current_start, current_end = lesson_range
    next_start = current_end + 1
    return re.compile(rf"(?<!\d){next_start}(?:~\d{{1,2}})?차시")


def sanitize_filename_part(value: str) -> str:
    cleaned = normalize_space(value)
    cleaned = re.sub(r'[<>:"/\\\\|?*]', "_", cleaned)
    cleaned = cleaned.replace("\n", " ").replace("\r", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ._")
    return cleaned


def normalize_unit_label(unit_text: Optional[str]) -> str:
    normalized = normalize_space(unit_text or "")
    if not normalized:
        return ""

    numbers = re.findall(r"\d+", normalized)
    if numbers:
        return f"{numbers[0]}단원"
    return normalized


def build_output_filename(pdf_path: str, exact_title: str, unit_text: Optional[str] = None) -> str:
    lesson_label, topic = parse_exact_title(exact_title)
    topic = strip_textbook_pages(topic)
    base_name = os.path.basename(pdf_path)
    name, ext = os.path.splitext(base_name)

    parts = [name]
    unit_label = normalize_unit_label(unit_text)
    if unit_label:
        parts.append(unit_label)
    if lesson_label:
        parts.append(lesson_label)
    if topic:
        parts.append(topic)
    parts.append("지도서발췌")

    safe_parts = [sanitize_filename_part(part) for part in parts if sanitize_filename_part(part)]
    return "_".join(safe_parts) + ext


def build_unique_output_path(path: Path) -> Path:
    if not path.exists():
        return path

    for index in range(1, 1000):
        candidate = path.with_name(f"{path.stem} ({index}){path.suffix}")
        if not candidate.exists():
            return candidate

    raise RuntimeError(f"저장할 수 있는 새 파일 이름을 찾지 못했습니다: {path}")


def build_search_targets(exact_title: str) -> List[str]:
    lesson_label, topic = parse_exact_title(exact_title)
    core_topic = strip_textbook_pages(topic)

    candidates = [
        core_topic,
        topic,
        f"{lesson_label} {core_topic}".strip(),
        lesson_label,
        exact_title,
    ]

    targets: List[str] = []
    for candidate in candidates:
        normalized = normalize_search_text(candidate)
        if normalized and normalized not in targets:
            targets.append(normalized)
    return targets


def normalize_markers(markers: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(normalize_search_text(marker) for marker in markers)


NORMALIZED_PLAN_PAGE_MARKERS = normalize_markers(PLAN_PAGE_MARKERS)
NORMALIZED_PLAN_LAYOUT_MARKERS = normalize_markers(PLAN_LAYOUT_MARKERS)
NORMALIZED_LESSON_START_MARKERS = normalize_markers(LESSON_START_MARKERS)
NORMALIZED_STRONG_LESSON_START_MARKERS = normalize_markers(STRONG_LESSON_START_MARKERS)
NORMALIZED_LESSON_SUPPORT_MARKERS = normalize_markers(LESSON_SUPPORT_MARKERS)
NORMALIZED_REFERENCE_PAGE_MARKERS = normalize_markers(REFERENCE_PAGE_MARKERS)


def is_noise_page(page_text: str) -> bool:
    normalized = normalize_search_text(page_text[:250])
    return any(marker in normalized for marker in ("목차", "차례", "부록"))


def split_normalized_lines(page_text: str, limit: Optional[int] = None) -> List[str]:
    lines = [normalize_search_text(line) for line in (page_text or "").splitlines()]
    filtered = [line for line in lines if line]
    if limit is not None:
        return filtered[:limit]
    return filtered


def marker_hits(normalized_text: str, markers: tuple[str, ...]) -> int:
    return sum(1 for marker in markers if marker and marker in normalized_text)


def best_target_score(
    normalized_page: str,
    top_lines: List[str],
    targets: List[str],
    *,
    base_score: int,
) -> int:
    best_score = -1
    top_block = "".join(top_lines[:14])
    top_head = top_lines[:3]
    top_window = top_lines[:8]

    for target in targets:
        if not target:
            continue
        position = normalized_page.find(target)
        if position == -1:
            continue

        score = base_score + len(target) * 2
        score += max(0, 1200 - min(position, 1200))
        if any(target in line for line in top_head):
            score += 1600
        elif any(target in line for line in top_window):
            score += 900
        elif target in top_block:
            score += 500
        best_score = max(best_score, score)

    return best_score


def score_page_for_title(page_text: str, exact_title: str) -> int:
    normalized_page = normalize_search_text(page_text)
    if not normalized_page or is_noise_page(page_text):
        return -1

    lesson_label, topic = parse_exact_title(exact_title)
    core_topic = strip_textbook_pages(topic)
    top_lines = split_normalized_lines(page_text, limit=18)
    top_block = "".join(top_lines)

    primary_targets = [
        normalize_search_text(candidate)
        for candidate in [
            core_topic,
            topic,
            f"{lesson_label} {core_topic}".strip(),
            exact_title,
        ]
        if normalize_search_text(candidate)
    ]
    fallback_targets = [normalize_search_text(lesson_label)] if lesson_label else []

    score = best_target_score(normalized_page, top_lines, primary_targets, base_score=3000)
    if score == -1:
        score = best_target_score(normalized_page, top_lines, fallback_targets, base_score=1200)
    if score == -1:
        return -1

    score += marker_hits(normalized_page, NORMALIZED_LESSON_START_MARKERS) * 650
    score += marker_hits(normalized_page, NORMALIZED_LESSON_SUPPORT_MARKERS) * 180

    textbook_target = extract_textbook_pages(exact_title)
    if textbook_target and textbook_target in normalized_page:
        score += 260
        if textbook_target in top_block:
            score += 180

    score -= marker_hits(normalized_page, NORMALIZED_PLAN_PAGE_MARKERS) * 2200
    if marker_hits(top_block, NORMALIZED_PLAN_LAYOUT_MARKERS) >= 3:
        score -= 1800
    score -= marker_hits(top_block, NORMALIZED_REFERENCE_PAGE_MARKERS) * 1200

    return score


def find_start_page(doc: "fitz.Document", exact_title: str) -> int:
    if not build_search_targets(exact_title):
        return -1

    best_page = -1
    best_score = -1

    for page_num in range(len(doc)):
        page_text = doc.load_page(page_num).get_text()
        score = score_page_for_title(page_text, exact_title)
        if score > best_score:
            best_score = score
            best_page = page_num

    return best_page


def is_next_lesson_start_page(page_text: str, next_lesson_pattern: re.Pattern[str]) -> bool:
    top_lines = (page_text or "").splitlines()[:20]
    compact_top_lines = [compact_lesson_text(line) for line in top_lines if compact_lesson_text(line)]
    if not any(next_lesson_pattern.search(line) for line in compact_top_lines):
        return False

    normalized_page = normalize_search_text(page_text)
    if not normalized_page or is_noise_page(page_text):
        return False
    if marker_hits(normalized_page, NORMALIZED_PLAN_PAGE_MARKERS):
        return False
    if marker_hits(normalized_page, NORMALIZED_REFERENCE_PAGE_MARKERS):
        return False
    if marker_hits(normalized_page, NORMALIZED_STRONG_LESSON_START_MARKERS) < 2:
        return False
    return True


def find_next_lesson_start_page(doc: "fitz.Document", start_page: int, exact_title: str) -> int:
    lesson_label, _topic = parse_exact_title(exact_title)
    next_lesson_pattern = build_next_lesson_pattern(lesson_label)
    if not next_lesson_pattern:
        return -1

    for page_num in range(start_page + 1, len(doc)):
        page_text = doc.load_page(page_num).get_text()
        if is_next_lesson_start_page(page_text, next_lesson_pattern):
            return page_num

    return -1


def find_end_page(doc: "fitz.Document", start_page: int, exact_title: str, extract_pages: int) -> int:
    next_lesson_start = find_next_lesson_start_page(doc, start_page, exact_title)
    if next_lesson_start != -1:
        return max(start_page, next_lesson_start - 1)
    return min(start_page + max(1, extract_pages) - 1, len(doc) - 1)


def do_extract(
    pdf_path: str,
    exact_title: str,
    *,
    unit_text: Optional[str] = None,
    extract_pages: int = 4,
) -> Optional[str]:
    if not FITZ_AVAILABLE:
        print("[!] PyMuPDF(fitz)가 없어 지도서 PDF를 추출할 수 없습니다. `pip install pymupdf` 후 다시 시도해 주세요.")
        return None

    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        print(f"[!] 지도서 PDF를 찾지 못했습니다: {pdf_file}")
        return None

    lesson_label, topic = parse_exact_title(exact_title)
    readable_topic = strip_textbook_pages(topic) or topic or exact_title

    print("\n[STEP 3] 지도서 PDF에서 해당 차시를 추출합니다...")
    print(f"  -> 대상 지도서: {pdf_file}")
    print(f"  -> 검색 기준: {readable_topic}")

    try:
        doc = fitz.open(str(pdf_file))
        start_page = find_start_page(doc, exact_title)
        if start_page == -1:
            print(f"[!] 지도서 PDF에서 '{readable_topic}' 관련 페이지를 찾지 못했습니다.")
            doc.close()
            return None

        end_page = find_end_page(doc, start_page, exact_title, extract_pages)
        new_doc = fitz.open()
        new_doc.insert_pdf(doc, from_page=start_page, to_page=end_page)

        out_filename = build_output_filename(str(pdf_file), exact_title, unit_text=unit_text)
        out_path = build_unique_output_path(pdf_file.with_name(out_filename))
        new_doc.save(str(out_path))
        new_doc.close()
        doc.close()

        print("[OK] 지도서 PDF 추출 완료")
        print(f"  - 추출 페이지: {start_page + 1} ~ {end_page + 1}")
        if unit_text or lesson_label:
            print(
                f"  - 차시 정보: {normalize_unit_label(unit_text) or '단원 미지정'} / "
                f"{lesson_label or '차시 미지정'}"
            )
        print(f"  - 저장 위치: {out_path}")

        try:
            os.startfile(str(out_path))
        except Exception:
            pass

        return str(out_path)
    except Exception as error:
        print(f"[!] 지도서 PDF 처리 중 오류가 발생했습니다: {error}")
        return None
