"""Pick which student PDF pages align with a blank template (batch scans, cover sheets)."""

from __future__ import annotations

from typing import Any

import numpy as np

from packages.student_extraction.template_alignment import align_page_images


def _mean_alignment_score(blank_pages: list[np.ndarray], student_slice: list[np.ndarray]) -> float:
    scores: list[float] = []
    for blank, student in zip(blank_pages, student_slice):
        try:
            scores.append(float(align_page_images(blank, student).score))
        except ValueError:
            scores.append(0.0)
    return sum(scores) / max(len(scores), 1)


def _page_ink_ratio(page: np.ndarray, *, ink_threshold: int = 245) -> float:
    return float(np.mean(np.asarray(page, dtype=np.uint8) < ink_threshold))


def _looks_like_trailing_blank_back_page(
    content_pages: list[np.ndarray],
    trailing_page: np.ndarray,
) -> bool:
    if not content_pages:
        return False

    content_ink_ratios = [_page_ink_ratio(page) for page in content_pages]
    trailing_ink_ratio = _page_ink_ratio(trailing_page)
    reference_ink_ratio = float(np.median(content_ink_ratios))
    mean_intensity = float(np.mean(np.asarray(trailing_page, dtype=np.uint8)))

    return (
        trailing_ink_ratio <= 0.02
        and trailing_ink_ratio <= max(reference_ink_ratio * 0.25, 0.005)
        and mean_intensity >= 240.0
    )


def select_student_pages_for_template(
    blank_pages: list[np.ndarray],
    student_pages: list[np.ndarray],
    *,
    fixed_offset: int | None = None,
    auto_pick: bool = True,
) -> tuple[list[np.ndarray], dict[str, Any]]:
    """Return the student page stack that matches the blank template length."""
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


def split_student_pages_for_template(
    blank_pages: list[np.ndarray],
    student_pages: list[np.ndarray],
    *,
    fixed_offset: int | None = None,
    auto_pick: bool = True,
) -> list[tuple[list[np.ndarray], dict[str, Any]]]:
    """Return one or more student page groups matching the blank template length.

    When the student PDF is an exact sequential multiple of the template length,
    treat it as a merged bundle of back-to-back students. Otherwise preserve the
    legacy single-window selection behavior.
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

    start_offset = fixed_offset or 0
    remaining_pages = n_s - start_offset
    duplex_scan_page_count = n_b + 1
    if remaining_pages >= duplex_scan_page_count and remaining_pages % duplex_scan_page_count == 0:
        total_groups = remaining_pages // duplex_scan_page_count
        duplex_groups: list[tuple[list[np.ndarray], dict[str, Any]]] = []
        for group_index in range(total_groups):
            scan_offset = start_offset + (group_index * duplex_scan_page_count)
            scan_slice = student_pages[scan_offset : scan_offset + duplex_scan_page_count]
            chosen = scan_slice[:n_b]
            trailing_page = scan_slice[-1]
            if not _looks_like_trailing_blank_back_page(chosen, trailing_page):
                duplex_groups = []
                break
            score = _mean_alignment_score(blank_pages, chosen)
            duplex_groups.append(
                (
                    chosen,
                    {
                        "mode": "duplex_groups",
                        "student_page_offset": scan_offset,
                        "student_pdf_page_count": n_s,
                        "template_page_count": n_b,
                        "mean_alignment_score": round(score, 4),
                        "group_index": group_index + 1,
                        "group_count": total_groups,
                        "scan_page_count": duplex_scan_page_count,
                        "ignored_trailing_page_offset": scan_offset + n_b,
                    },
                )
            )
        if duplex_groups:
            return duplex_groups

    if remaining_pages > n_b and remaining_pages % n_b == 0:
        total_groups = remaining_pages // n_b
        groups: list[tuple[list[np.ndarray], dict[str, Any]]] = []
        for group_index in range(total_groups):
            group_offset = start_offset + (group_index * n_b)
            chosen = student_pages[group_offset : group_offset + n_b]
            score = _mean_alignment_score(blank_pages, chosen)
            groups.append(
                (
                    chosen,
                    {
                        "mode": "sequential_groups",
                        "student_page_offset": group_offset,
                        "student_pdf_page_count": n_s,
                        "template_page_count": n_b,
                        "mean_alignment_score": round(score, 4),
                        "group_index": group_index + 1,
                        "group_count": total_groups,
                    },
                )
            )
        return groups

    selected_pages, meta = select_student_pages_for_template(
        blank_pages,
        student_pages,
        fixed_offset=fixed_offset,
        auto_pick=auto_pick,
    )
    return [(selected_pages, meta)]
