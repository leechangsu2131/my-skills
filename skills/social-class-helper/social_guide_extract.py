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


def is_noise_page(page_text: str) -> bool:
    normalized = normalize_search_text(page_text[:250])
    return any(marker in normalized for marker in ("목차", "차례", "부록"))


def find_start_page(doc: "fitz.Document", exact_title: str) -> int:
    targets = build_search_targets(exact_title)
    if not targets:
        return -1

    best_page = -1
    best_score = 0

    for page_num in range(len(doc)):
        page_text = doc.load_page(page_num).get_text()
        normalized_page = normalize_search_text(page_text)
        if not normalized_page or is_noise_page(page_text):
            continue

        for target in targets:
            if target and target in normalized_page:
                score = len(target)
                if score > best_score:
                    best_score = score
                    best_page = page_num
                break

    return best_page


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

        end_page = min(start_page + max(1, extract_pages) - 1, len(doc) - 1)
        new_doc = fitz.open()
        new_doc.insert_pdf(doc, from_page=start_page, to_page=end_page)

        out_filename = build_output_filename(str(pdf_file), exact_title, unit_text=unit_text)
        out_path = pdf_file.with_name(out_filename)
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
