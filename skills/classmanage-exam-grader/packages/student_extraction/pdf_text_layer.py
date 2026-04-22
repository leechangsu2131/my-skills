from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import fitz


def _dpi_scale(dpi: int) -> float:
    return float(dpi) / 72.0


def extract_line_detections_from_pdf_text_layer(
    pdf_path: Path,
    *,
    dpi: int = 160,
) -> dict[int, list[dict]]:
    """Build OCR-like line detections from PDF text layers."""
    scale = _dpi_scale(dpi)
    detections_by_page: dict[int, list[dict]] = {}
    document = fitz.open(pdf_path)
    try:
        for page_index, page in enumerate(document):
            words = page.get_text("words")
            grouped: dict[tuple[int, int], list[tuple[float, float, float, float, str]]] = defaultdict(list)
            for word in words:
                x0, y0, x1, y1, text, block_no, line_no, _word_no = word
                grouped[(int(block_no), int(line_no))].append((x0, y0, x1, y1, str(text)))

            lines: list[dict] = []
            for line_words in grouped.values():
                line_words.sort(key=lambda item: item[0])
                line_text = " ".join(item[4] for item in line_words).strip()
                if not line_text:
                    continue
                xs0 = [item[0] for item in line_words]
                ys0 = [item[1] for item in line_words]
                xs1 = [item[2] for item in line_words]
                ys1 = [item[3] for item in line_words]
                lines.append(
                    {
                        "text": line_text,
                        "confidence": 1.0,
                        "bbox": [
                            float(min(xs0) * scale),
                            float(min(ys0) * scale),
                            float(max(xs1) * scale),
                            float(max(ys1) * scale),
                        ],
                    }
                )

            lines.sort(key=lambda item: (item["bbox"][1], item["bbox"][0]))
            detections_by_page[page_index] = lines
    finally:
        document.close()
    return detections_by_page


def has_enough_text_layer_content(
    detections_by_page: dict[int, list[dict]],
    *,
    min_lines_per_page: int = 4,
) -> bool:
    if not detections_by_page:
        return False
    return all(len(lines) >= min_lines_per_page for lines in detections_by_page.values())


def extract_text_from_render_bbox(
    pdf_path: Path,
    *,
    page_index: int,
    render_bbox: list[float],
    dpi: int = 160,
) -> str:
    """Extract text from a rendered-pixel bbox by converting to PDF point units."""
    scale = _dpi_scale(dpi)
    x1, y1, x2, y2 = render_bbox
    page_rect = fitz.Rect(x1 / scale, y1 / scale, x2 / scale, y2 / scale)

    if page_rect.width <= 0 or page_rect.height <= 0:
        return ""

    document = fitz.open(pdf_path)
    try:
        if page_index < 0 or page_index >= len(document):
            return ""
        page = document[page_index]
        words = page.get_text("words")
        selected: list[tuple[float, float, str]] = []
        for word in words:
            wx0, wy0, wx1, wy1, text, _b, _l, _w = word
            word_rect = fitz.Rect(wx0, wy0, wx1, wy1)
            overlap = word_rect & page_rect
            if overlap.is_empty:
                continue
            overlap_ratio = overlap.get_area() / max(word_rect.get_area(), 1e-6)
            if overlap_ratio >= 0.35:
                selected.append((wy0, wx0, str(text)))

        selected.sort(key=lambda item: (item[0], item[1]))
        return " ".join(item[2] for item in selected).strip()
    finally:
        document.close()
