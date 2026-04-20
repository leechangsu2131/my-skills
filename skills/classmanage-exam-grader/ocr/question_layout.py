from __future__ import annotations

from dataclasses import dataclass
import re

import layoutparser as lp


@dataclass(slots=True)
class QuestionRegion:
    q_num: int
    page_index: int
    anchor_bbox: list[float]
    answer_bbox: list[float]


@dataclass(slots=True)
class QuestionLayout:
    items: list[QuestionRegion]


QUESTION_RE = re.compile(r"^(\d+)[\.\)]?$")
ANCHOR_MIN_CONFIDENCE = 0.35
ANSWER_LEFT_PADDING = 12.0
ANSWER_TOP_PADDING = 8.0
ANSWER_BOTTOM_PADDING = 8.0
ANSWER_RIGHT_MARGIN = 24.0
MIN_ANSWER_HEIGHT = 12.0


def parse_question_anchor_text(raw: str) -> int | None:
    """Map OCR line text to a question number when it looks like an item label."""
    text = str(raw).strip()
    if not text:
        return None

    simple = QUESTION_RE.match(text)
    if simple:
        return int(simple.group(1))

    paren = re.match(r"^\((\d{1,3})\)\s*$", text)
    if paren:
        return int(paren.group(1))

    hangul = re.match(r"^(?:문항\s*)?(\d{1,3})\s*[\.:\)]", text)
    if hangul:
        return int(hangul.group(1))

    q_prefix = re.match(r"^[Qq]\s*(\d{1,3})\s*$", text)
    if q_prefix:
        return int(q_prefix.group(1))

    return None


def build_question_layout(
    detections_by_page: dict[int, list[dict]],
    page_sizes: dict[int, tuple[int, int]],
) -> QuestionLayout:
    items: list[QuestionRegion] = []

    for page_index, detections in detections_by_page.items():
        anchors: list[tuple[int, lp.TextBlock]] = []
        for detection in detections:
            q_num = parse_question_anchor_text(str(detection["text"]))
            if q_num is not None:
                confidence = float(detection.get("confidence", 1.0))
                if confidence < ANCHOR_MIN_CONFIDENCE:
                    continue
                anchors.append((q_num, _to_text_block(detection)))

        anchors = _deduplicate_anchors(anchors)

        anchors.sort(key=lambda item: (item[1].coordinates[1], item[1].coordinates[0], item[0]))
        page_width, page_height = page_sizes[page_index]
        for index, (q_num, anchor) in enumerate(anchors):
            x1, y1, x2, y2 = [float(value) for value in anchor.coordinates]
            next_top = (
                float(anchors[index + 1][1].coordinates[1]) if index + 1 < len(anchors) else float(page_height - 20)
            )
            answer_rect = lp.Rectangle(
                x_1=x2 + ANSWER_LEFT_PADDING,
                y_1=max(y1 - ANSWER_TOP_PADDING, 0.0),
                x_2=max(float(page_width) - ANSWER_RIGHT_MARGIN, x2 + ANSWER_LEFT_PADDING + 1.0),
                y_2=min(next_top - ANSWER_BOTTOM_PADDING, float(page_height - 1)),
            )
            answer_bbox = _normalize_bbox(answer_rect, page_width, page_height, min_height=MIN_ANSWER_HEIGHT)
            items.append(
                QuestionRegion(
                    q_num=q_num,
                    page_index=page_index,
                    anchor_bbox=[x1, y1, x2, y2],
                    answer_bbox=answer_bbox,
                )
            )

    items.sort(key=lambda item: (item.page_index, item.q_num))
    return QuestionLayout(items=items)


def _to_text_block(detection: dict) -> lp.TextBlock:
    x1, y1, x2, y2 = [float(value) for value in detection["bbox"]]
    rect = lp.Rectangle(x_1=x1, y_1=y1, x_2=x2, y_2=y2)
    return lp.TextBlock(
        block=rect,
        text=str(detection.get("text", "")),
        score=float(detection.get("confidence", 1.0)),
    )


def _deduplicate_anchors(anchors: list[tuple[int, lp.TextBlock]]) -> list[tuple[int, lp.TextBlock]]:
    """Keep one anchor per question number to avoid OCR duplicates."""
    best_by_question: dict[int, tuple[int, lp.TextBlock]] = {}
    for q_num, block in anchors:
        current = best_by_question.get(q_num)
        if current is None:
            best_by_question[q_num] = (q_num, block)
            continue
        # Prefer higher OCR confidence; if tied, prefer upper-most block.
        current_score = float(current[1].score or 0.0)
        next_score = float(block.score or 0.0)
        if (next_score, -block.coordinates[1]) > (current_score, -current[1].coordinates[1]):
            best_by_question[q_num] = (q_num, block)
    return list(best_by_question.values())


def _normalize_bbox(
    rect: lp.Rectangle,
    page_width: int,
    page_height: int,
    *,
    min_height: float,
) -> list[float]:
    x1, y1, x2, y2 = [float(value) for value in rect.coordinates]
    clamped_x1 = max(0.0, min(x1, float(page_width - 1)))
    clamped_y1 = max(0.0, min(y1, float(page_height - 1)))
    clamped_x2 = max(clamped_x1 + 1.0, min(x2, float(page_width - 1)))
    desired_y2 = max(clamped_y1 + min_height, min(y2, float(page_height - 1)))
    clamped_y2 = min(desired_y2, float(page_height - 1))
    if clamped_y2 <= clamped_y1:
        clamped_y2 = min(clamped_y1 + 1.0, float(page_height - 1))
    return [clamped_x1, clamped_y1, clamped_x2, clamped_y2]
