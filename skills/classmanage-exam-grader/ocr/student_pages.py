"""Pick which student PDF pages align with a blank template (batch scans, cover sheets)."""

from __future__ import annotations

from typing import Any

import numpy as np

from ocr.template_alignment import align_page_images


def _mean_alignment_score(blank_pages: list[np.ndarray], student_slice: list[np.ndarray]) -> float:
    scores: list[float] = []
    for blank, student in zip(blank_pages, student_slice):
        try:
            scores.append(float(align_page_images(blank, student).score))
        except ValueError:
            scores.append(0.0)
    return sum(scores) / max(len(scores), 1)


def select_student_pages_for_template(
    blank_pages: list[np.ndarray],
    student_pages: list[np.ndarray],
    *,
    fixed_offset: int | None = None,
    auto_pick: bool = True,
) -> tuple[list[np.ndarray], dict[str, Any]]:
    """Return the student page stack that matches the blank template length.

    When the scan contains extra leading/trailing pages, either pass a 0-based
    ``fixed_offset`` (skip the first *offset* pages) or enable ``auto_pick`` to
    search for the contiguous window with the best average ORB/AKAZE alignment score.
    """
    n_b = len(blank_pages)
    n_s = len(student_pages)
    if n_b == 0:
        raise ValueError("Blank exam has no pages.")
    if n_s == 0:
        raise ValueError("Student PDF has no pages.")

    if n_s < n_b:
        raise ValueError(
            f"Student PDF has fewer pages ({n_s}) than the blank template ({n_b}). "
            "Use a complete scan or split the file so exam pages match the template."
        )

    if n_s == n_b:
        # Per-page alignment runs later in the OCR pipeline; avoid duplicate work here.
        meta = {
            "mode": "equal_length",
            "student_page_offset": 0,
            "student_pdf_page_count": n_s,
            "template_page_count": n_b,
            "mean_alignment_score": None,
        }
        return student_pages, meta

    max_offset = n_s - n_b

    if fixed_offset is not None:
        if fixed_offset < 0 or fixed_offset > max_offset:
            raise ValueError(
                f"student_page_offset must be between 0 and {max_offset} "
                f"(student has {n_s} pages, template has {n_b})."
            )
        chosen = student_pages[fixed_offset : fixed_offset + n_b]
        score = _mean_alignment_score(blank_pages, chosen)
        meta = {
            "mode": "fixed_offset",
            "student_page_offset": fixed_offset,
            "student_pdf_page_count": n_s,
            "template_page_count": n_b,
            "mean_alignment_score": round(score, 4),
        }
        return chosen, meta

    if not auto_pick:
        raise ValueError(
            f"Student PDF has {n_s} pages but the blank template has {n_b}. "
            f"Either upload a trimmed PDF, set student_page_offset (0..{max_offset}), "
            "or enable automatic page-window selection."
        )

    best_offset = 0
    best_score = -1.0
    for offset in range(0, max_offset + 1):
        window = student_pages[offset : offset + n_b]
        score = _mean_alignment_score(blank_pages, window)
        if score > best_score:
            best_score = score
            best_offset = offset

    chosen = student_pages[best_offset : best_offset + n_b]
    meta = {
        "mode": "auto_window",
        "student_page_offset": best_offset,
        "student_pdf_page_count": n_s,
        "template_page_count": n_b,
        "mean_alignment_score": round(best_score, 4),
        "candidates_evaluated": max_offset + 1,
    }
    return chosen, meta
