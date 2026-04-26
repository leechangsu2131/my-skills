from __future__ import annotations

from typing import Any

import cv2
import numpy as np


def localize_multiple_choice_answer_bbox(
    page: Any,
    *,
    question_bbox: list[float],
    anchor_bbox: list[float],
    fallback_bbox: list[float],
    prompt_bbox: list[float] | None = None,
) -> tuple[list[float], str]:
    search_prompt_bbox = prompt_bbox or _build_prompt_line_bbox(page, question_bbox=question_bbox, anchor_bbox=anchor_bbox)
    parenthesized = _detect_parenthesized_blank_bbox(page, search_prompt_bbox)
    if parenthesized is not None:
        return parenthesized, "parenthesized_blank"

    choice_box = _detect_rectangular_choice_box_bbox(page, question_bbox=question_bbox, anchor_bbox=anchor_bbox)
    if choice_box is not None:
        return choice_box, "choice_box"

    labeled_choice_line = _detect_labeled_choice_answer_line_bbox(
        page,
        question_bbox=question_bbox,
        anchor_bbox=anchor_bbox,
    )
    if labeled_choice_line is not None:
        return labeled_choice_line, "labeled_choice_answer_line"

    choice_line = _detect_choice_answer_line_bbox(page, question_bbox=question_bbox, anchor_bbox=anchor_bbox)
    if choice_line is not None:
        return choice_line, "choice_answer_line"

    return _build_prompt_line_fallback_bbox(search_prompt_bbox, anchor_bbox, fallback_bbox), "prompt_choice"


def localize_short_answer_bbox(
    page: Any,
    *,
    question_bbox: list[float],
    anchor_bbox: list[float],
    prompt_bbox: list[float] | None = None,
) -> tuple[list[float], str]:
    search_prompt_bbox = prompt_bbox or _build_prompt_line_bbox(page, question_bbox=question_bbox, anchor_bbox=anchor_bbox)
    parenthesized = _detect_parenthesized_blank_bbox(page, search_prompt_bbox)
    if parenthesized is not None:
        return parenthesized, "parenthesized_blank"

    labeled_choice_line = _detect_labeled_choice_answer_line_bbox(
        page,
        question_bbox=question_bbox,
        anchor_bbox=anchor_bbox,
    )
    if labeled_choice_line is not None:
        return labeled_choice_line, "labeled_choice_answer_line"

    answer_line = _detect_choice_answer_line_bbox(
        page,
        question_bbox=question_bbox,
        anchor_bbox=anchor_bbox,
    )
    if answer_line is not None:
        return answer_line, "answer_line"

    return [float(value) for value in question_bbox], "blank"


def _detect_parenthesized_blank_bbox(page: Any, question_bbox: list[float]) -> list[float] | None:
    crop, origin_x, origin_y = _crop_with_origin(page, question_bbox)
    if crop.size == 0:
        return None

    height, width = crop.shape[:2]
    if height < 24 or width < 80:
        return None

    # Objective answer blanks often sit after a long prompt with wide empty space.
    # Start searching earlier than the far-right tail so wrapped questions still include `(   )`.
    search_x1 = int(round(width * 0.28))
    search_y1 = int(round(height * 0.05))
    search_y2 = max(search_y1 + 1, int(round(height * 0.82)))
    search = crop[search_y1:search_y2, search_x1:]
    if search.size == 0:
        return None

    binary = _binary_ink(search)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    components: list[tuple[int, int, int, int]] = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if h < max(int(search.shape[0] * 0.10), 8):
            continue
        if h > int(search.shape[0] * 0.95):
            continue
        if w < 2 or w > max(int(search.shape[1] * 0.10), 20):
            continue
        if h / max(w, 1) < 1.6:
            continue
        components.append((x, y, w, h))

    if len(components) < 2:
        return None

    best_pair: tuple[tuple[int, int, int, int], tuple[int, int, int, int]] | None = None
    best_score = float("-inf")
    sorted_components = sorted(components, key=lambda item: item[0])
    for index in range(len(sorted_components) - 1):
        left = sorted_components[index]
        right = sorted_components[index + 1]
        lx, ly, lw, lh = left
        rx, ry, rw, rh = right
        gap = rx - (lx + lw)
        if gap < max(int(search.shape[1] * 0.03), 10):
            continue
        if gap > max(int(search.shape[1] * 0.30), 96):
            continue
        overlap_top = max(ly, ry)
        overlap_bottom = min(ly + lh, ry + rh)
        overlap = overlap_bottom - overlap_top
        if overlap < min(lh, rh) * 0.55:
            continue
        interior = binary[overlap_top:overlap_bottom, lx + lw : rx]
        if interior.size == 0:
            continue
        if float(np.mean(interior > 0)) > 0.08:
            continue
        width_ratio = gap / max(min(lh, rh), 1)
        if not 0.35 <= width_ratio <= 2.4:
            continue
        pair_mid_y = (ly + lh / 2.0 + ry + rh / 2.0) / 2.0
        vertical_penalty = abs((ly + lh / 2.0) - (ry + rh / 2.0))
        pair_mid_x = ((lx + lw / 2.0) + (rx + rw / 2.0)) / 2.0
        score = (
            (gap * 1.6)
            + overlap
            - (vertical_penalty * 1.3)
            - abs(pair_mid_y - (search.shape[0] * 0.52))
            + (pair_mid_x * 0.18)
        )
        if score > best_score:
            best_score = score
            best_pair = (left, right)

    if best_pair is None:
        return None

    left, right = best_pair
    lx, ly, lw, lh = left
    rx, ry, rw, rh = right
    x1 = origin_x + search_x1 + max(lx - 4, 0)
    y1 = origin_y + search_y1 + max(min(ly, ry) - 4, 0)
    x2 = origin_x + search_x1 + min(rx + rw + 4, search.shape[1])
    y2 = origin_y + search_y1 + min(max(ly + lh, ry + rh) + 4, search.shape[0])
    return [float(x1), float(y1), float(x2), float(y2)]

def _build_prompt_line_bbox(
    page: Any,
    *,
    question_bbox: list[float],
    anchor_bbox: list[float],
) -> list[float]:
    qx1, qy1, qx2, qy2 = [float(value) for value in question_bbox]
    ax1, ay1, ax2, ay2 = [float(value) for value in anchor_bbox]
    anchor_height = max(ay2 - ay1, 1.0)
    right = min(qx2, ax2 + max(anchor_height * 16.0, 360.0))
    return [
        max(0.0, qx1),
        max(0.0, ay1 - 12.0),
        min(float(page.shape[1] - 1), right),
        min(float(page.shape[0] - 1), min(qy2, ay2 + max(anchor_height * 2.8, 42.0))),
    ]


def _build_prompt_line_fallback_bbox(
    prompt_bbox: list[float],
    anchor_bbox: list[float],
    fallback_bbox: list[float],
) -> list[float]:
    px1, py1, px2, py2 = [float(value) for value in prompt_bbox]
    _fx1, fy1, _fx2, fy2 = [float(value) for value in fallback_bbox]
    _ax1, ay1, ax2, ay2 = [float(value) for value in anchor_bbox]
    prompt_width = max(px2 - px1, 1.0)
    x1 = max(ax2 + 18.0, px2 - max(prompt_width * 0.22, 72.0))
    y1 = max(py1, ay1 - 4.0, fy1)
    y2 = max(y1 + 16.0, min(py2, ay2 + max(ay2 - ay1, 18.0), fy2))
    return [float(x1), float(y1), float(px2 - 6.0), float(y2)]


def _detect_rectangular_choice_box_bbox(
    page: Any,
    *,
    question_bbox: list[float],
    anchor_bbox: list[float],
) -> list[float] | None:
    crop, origin_x, origin_y = _crop_with_origin(page, question_bbox)
    if crop.size == 0:
        return None

    height, width = crop.shape[:2]
    if height < 28 or width < 90:
        return None

    binary = _binary_ink(crop)
    contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    min_x = max(int(round(anchor_bbox[2] - question_bbox[0] + 10.0)), int(round(width * 0.28)))
    top_limit = max(int(round(anchor_bbox[1] - question_bbox[1] - 10.0)), 0)
    bottom_limit = min(int(round(height * 0.92)), height - 1)
    best_bbox: tuple[int, int, int, int] | None = None
    best_score = float("-inf")

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if x < min_x:
            continue
        if y < top_limit or y + h > bottom_limit:
            continue
        if w < max(int(width * 0.08), 24) or w > max(int(width * 0.30), 96):
            continue
        if h < 14 or h > max(int(height * 0.40), 44):
            continue
        aspect_ratio = w / max(float(h), 1.0)
        if not 1.1 <= aspect_ratio <= 4.8:
            continue

        roi = binary[y : y + h, x : x + w]
        if roi.size == 0:
            continue
        border = max(min(w, h) // 8, 2)
        if h <= border * 2 or w <= border * 2:
            continue
        inner = roi[border:-border, border:-border]
        border_pixels = np.concatenate(
            [
                roi[:border, :].ravel(),
                roi[-border:, :].ravel(),
                roi[:, :border].ravel(),
                roi[:, -border:].ravel(),
            ]
        )
        border_ink = float(np.mean(border_pixels > 0))
        inner_ink = float(np.mean(inner > 0)) if inner.size else 0.0
        if border_ink < 0.22:
            continue
        if inner_ink > max(0.20, border_ink * 0.8):
            continue

        score = (w * h) + (x * 0.6) - (abs((y + (h / 2.0)) - (height * 0.48)) * 1.3)
        if score > best_score:
            best_score = score
            best_bbox = (x, y, w, h)

    if best_bbox is None:
        return None

    x, y, w, h = best_bbox
    return [
        float(origin_x + max(x - 4, 0)),
        float(origin_y + max(y - 4, 0)),
        float(origin_x + min(x + w + 4, width)),
        float(origin_y + min(y + h + 4, height)),
    ]


def _detect_choice_answer_line_bbox(
    page: Any,
    *,
    question_bbox: list[float],
    anchor_bbox: list[float],
) -> list[float] | None:
    crop, origin_x, origin_y = _crop_with_origin(page, question_bbox)
    if crop.size == 0:
        return None

    height, width = crop.shape[:2]
    if height < 24 or width < 90:
        return None

    binary = _binary_ink(crop)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(width // 5, 42), 1))
    horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    contours, _ = cv2.findContours(horizontal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    min_x = max(int(round(anchor_bbox[2] - question_bbox[0] + 10.0)), int(round(width * 0.28)))
    min_y = max(int(round(anchor_bbox[1] - question_bbox[1])), int(round(height * 0.18)))
    best_bbox: tuple[int, int, int, int] | None = None
    best_score = float("-inf")

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if x < min_x or y < min_y:
            continue
        if w < max(int(width * 0.16), 54):
            continue
        if h > max(6, height // 12):
            continue

        line_band = crop[max(y - 5, 0) : min(y + h + 6, height), x : min(x + w, width)]
        if line_band.size == 0:
            continue
        ink_ratio = float((line_band < 220).mean())
        if ink_ratio < 0.10:
            continue

        score = (w * 1.8) + (x * 0.35) + (y * 0.25)
        if score > best_score:
            best_score = score
            best_bbox = (x, y, w, h)

    if best_bbox is None:
        return None

    x, y, w, h = best_bbox
    return [
        float(origin_x + max(x - 6, 0)),
        float(origin_y + max(y - 10, 0)),
        float(origin_x + min(x + w + 6, width)),
        float(origin_y + min(y + h + 12, height)),
    ]


def _detect_labeled_choice_answer_line_bbox(
    page: Any,
    *,
    question_bbox: list[float],
    anchor_bbox: list[float],
) -> list[float] | None:
    crop, origin_x, origin_y = _crop_with_origin(page, question_bbox)
    if crop.size == 0:
        return None

    height, width = crop.shape[:2]
    if height < 40 or width < 120:
        return None

    binary = _binary_ink(crop)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(width // 6, 48), 1))
    horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    contours, _ = cv2.findContours(horizontal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    min_x = max(int(round(anchor_bbox[2] - question_bbox[0] + 10.0)), int(round(width * 0.28)))
    min_y = max(int(round(height * 0.42)), int(round(anchor_bbox[1] - question_bbox[1] + 18.0)))
    best_bbox: tuple[int, int, int, int] | None = None
    best_score = float("-inf")

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if x < min_x or y < min_y:
            continue
        if w < max(int(width * 0.10), 48):
            continue
        if h > max(6, height // 12):
            continue

        probe_left = max(x - max(int(width * 0.12), 42), 0)
        probe_top = max(y - 18, 0)
        probe_bottom = min(y + h + 18, height)
        bubble_probe = binary[probe_top:probe_bottom, probe_left:x]
        if bubble_probe.size == 0:
            continue

        ink_ratio = float(np.mean(bubble_probe > 0))
        if ink_ratio < 0.12:
            continue

        probe_contours, _ = cv2.findContours(bubble_probe, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        bubble_score = 0.0
        for probe_contour in probe_contours:
            bx, by, bw, bh = cv2.boundingRect(probe_contour)
            area = bw * bh
            if area < 32:
                continue
            if bh < 8 or bw < 8:
                continue
            aspect_ratio = bw / max(float(bh), 1.0)
            if not 0.5 <= aspect_ratio <= 1.9:
                continue
            bubble_score = max(bubble_score, float(area))
        if bubble_score <= 0.0:
            continue

        score = (bubble_score * 0.9) + (y * 1.3) + (w * 0.35)
        if score > best_score:
            best_score = score
            best_bbox = (x, y, w, h)

    if best_bbox is None:
        return None

    x, y, w, h = best_bbox
    return [
        float(origin_x + max(x - 6, 0)),
        float(origin_y + max(y - 12, 0)),
        float(origin_x + min(x + w + 6, width)),
        float(origin_y + min(y + h + 14, height)),
    ]


def _crop_with_origin(page: Any, bbox: list[float]) -> tuple[Any, int, int]:
    x1, y1, x2, y2 = [int(round(float(value))) for value in bbox]
    x1 = max(x1, 0)
    y1 = max(y1, 0)
    x2 = min(max(x2, x1 + 1), page.shape[1])
    y2 = min(max(y2, y1 + 1), page.shape[0])
    return page[y1:y2, x1:x2], x1, y1


def _binary_ink(image: Any) -> Any:
    if image.ndim == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return binary
