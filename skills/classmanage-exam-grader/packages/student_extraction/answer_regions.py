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
) -> tuple[list[float], str]:
    prompt_bbox = _build_prompt_line_bbox(page, question_bbox=question_bbox, anchor_bbox=anchor_bbox)
    parenthesized = _detect_parenthesized_blank_bbox(page, prompt_bbox)
    if parenthesized is not None:
        return parenthesized, "parenthesized_blank"

    return _build_prompt_line_fallback_bbox(prompt_bbox, anchor_bbox, fallback_bbox), "prompt_choice"


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
