from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(slots=True)
class QuestionRegion:
    q_num: int
    page_index: int
    anchor_bbox: list[float]
    answer_bbox: list[float]
    question_text_snippet: str = ""
    answer_marker_type: str = "빈줄"
    question_text_bbox: list[float] | None = None
    question_bbox: list[float] | None = None
    extraction_mode: str = "crop_ocr"


@dataclass(slots=True)
class QuestionLayout:
    items: list[QuestionRegion]


@dataclass(slots=True)
class Rectangle:
    x_1: float
    y_1: float
    x_2: float
    y_2: float

    @property
    def coordinates(self) -> tuple[float, float, float, float]:
        return (self.x_1, self.y_1, self.x_2, self.y_2)


@dataclass(slots=True)
class TextBlock:
    block: Rectangle
    text: str
    score: float
    source_block: Rectangle | None = None

    @property
    def coordinates(self) -> tuple[float, float, float, float]:
        return self.block.coordinates

    @property
    def source_coordinates(self) -> tuple[float, float, float, float]:
        if self.source_block is None:
            return self.block.coordinates
        return self.source_block.coordinates


QUESTION_RE = re.compile(r"^(\d+)[\.\)]$")
QUESTION_SCORE_RE = re.compile(r"^\[\s*\d+\s*점\s*\]$")
ANCHOR_MIN_CONFIDENCE = 0.35
TOP_HEADER_RATIO = 0.08
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
        page_width, page_height = page_sizes[page_index]
        anchors: list[tuple[int, TextBlock]] = []
        for detection in detections:
            q_num = parse_question_anchor_text(str(detection["text"]))
            if q_num is not None:
                confidence = float(detection.get("confidence", 1.0))
                if confidence < ANCHOR_MIN_CONFIDENCE:
                    continue
                anchors.append((q_num, _to_anchor_text_block(detection)))

        anchors = _deduplicate_anchors(anchors, page_width=page_width, page_height=page_height)
        anchors = [
            (q_num, block)
            for q_num, block in anchors
            if _should_keep_anchor(q_num, block, page_width=page_width, page_height=page_height)
        ]
        anchors.sort(key=lambda item: (item[1].coordinates[1], item[1].coordinates[0], item[0]))
        column_split_x = _estimate_column_split(anchors, page_width)
        for q_num, anchor in anchors:
            x1, y1, x2, y2 = [float(value) for value in anchor.coordinates]
            column = _resolve_column(x1, column_split_x)
            next_top = _find_next_top_in_column(anchors, anchor, column_split_x, page_height)
            column_end = _column_right_boundary(column, column_split_x, page_width)
            question_text_snippet, answer_marker_type, question_text_bbox = _extract_question_metadata(
                detections,
                anchor,
                page_width=int(column_end),
                block_bottom=next_top,
            )
            answer_rect = Rectangle(
                x_1=x2 + ANSWER_LEFT_PADDING,
                y_1=max(y1 - ANSWER_TOP_PADDING, 0.0),
                x_2=max(column_end - ANSWER_RIGHT_MARGIN, x2 + ANSWER_LEFT_PADDING + 1.0),
                y_2=min(next_top - ANSWER_BOTTOM_PADDING, float(page_height - 1)),
            )
            answer_bbox = _normalize_bbox(answer_rect, page_width, page_height, min_height=MIN_ANSWER_HEIGHT)
            items.append(
                QuestionRegion(
                    q_num=q_num,
                    page_index=page_index,
                    anchor_bbox=[x1, y1, x2, y2],
                    answer_bbox=answer_bbox,
                    question_text_snippet=question_text_snippet,
                    answer_marker_type=answer_marker_type,
                    question_text_bbox=question_text_bbox,
                )
            )

    items.sort(key=lambda item: (item.page_index, item.q_num))
    return QuestionLayout(items=items)


def _to_text_block(detection: dict) -> TextBlock:
    x1, y1, x2, y2 = [float(value) for value in detection["bbox"]]
    rect = Rectangle(x_1=x1, y_1=y1, x_2=x2, y_2=y2)
    return TextBlock(
        block=rect,
        text=str(detection.get("text", "")),
        score=float(detection.get("confidence", 1.0)),
        source_block=rect,
    )


def _to_anchor_text_block(detection: dict) -> TextBlock:
    block = _to_text_block(detection)
    text = block.text.strip()
    if parse_question_anchor_text(text) is None or len(text) <= 4:
        return block
    x1, y1, x2, y2 = [float(value) for value in block.coordinates]
    anchor_width = max((y2 - y1) * 1.6, 18.0)
    return TextBlock(
        block=Rectangle(x_1=x1, y_1=y1, x_2=min(x2, x1 + anchor_width), y_2=y2),
        text=text,
        score=block.score,
        source_block=block.source_block,
    )


def _deduplicate_anchors(
    anchors: list[tuple[int, TextBlock]],
    *,
    page_width: int,
    page_height: int,
) -> list[tuple[int, TextBlock]]:
    """Keep one anchor per question number to avoid OCR duplicates."""
    best_by_question: dict[int, tuple[int, TextBlock]] = {}
    for q_num, block in anchors:
        current = best_by_question.get(q_num)
        if current is None:
            best_by_question[q_num] = (q_num, block)
            continue
        current_header = _is_top_header_anchor(current[1], page_width=page_width, page_height=page_height)
        next_header = _is_top_header_anchor(block, page_width=page_width, page_height=page_height)
        if current_header != next_header:
            if not next_header:
                best_by_question[q_num] = (q_num, block)
            continue
        current_score = float(current[1].score or 0.0)
        next_score = float(block.score or 0.0)
        current_width = float(current[1].coordinates[2] - current[1].coordinates[0])
        next_width = float(block.coordinates[2] - block.coordinates[0])
        if next_width < current_width * 0.75:
            best_by_question[q_num] = (q_num, block)
            continue
        if current_width < next_width * 0.75:
            continue
        if (next_score, -block.coordinates[1]) > (current_score, -current[1].coordinates[1]):
            best_by_question[q_num] = (q_num, block)
    return list(best_by_question.values())


def _should_keep_anchor(
    q_num: int,
    block: TextBlock,
    *,
    page_width: int,
    page_height: int,
) -> bool:
    if q_num <= 0:
        return False
    if _is_top_header_anchor(block, page_width=page_width, page_height=page_height):
        return False
    return True


def _is_top_header_anchor(
    block: TextBlock,
    *,
    page_width: int,
    page_height: int,
) -> bool:
    x1, y1, _x2, y2 = [float(value) for value in block.coordinates]
    header_band = min(float(page_height) * TOP_HEADER_RATIO, 32.0)
    center_y = (y1 + y2) / 2.0
    return center_y <= header_band and x1 > float(page_width) * 0.10 and y1 < header_band


def _estimate_column_split(anchors: list[tuple[int, TextBlock]], page_width: int) -> float | None:
    if len(anchors) < 2:
        return None
    centers = sorted((block.coordinates[0] + block.coordinates[2]) / 2.0 for _q_num, block in anchors)
    gaps = [
        (centers[index + 1] - centers[index], index)
        for index in range(len(centers) - 1)
    ]
    if not gaps:
        return None
    largest_gap, gap_index = max(gaps, key=lambda item: item[0])
    if largest_gap < float(page_width) * 0.12:
        return None
    return (centers[gap_index] + centers[gap_index + 1]) / 2.0


def _resolve_column(x1: float, column_split_x: float | None) -> str:
    if column_split_x is None:
        return "full"
    return "left" if x1 < column_split_x else "right"


def _find_next_top_in_column(
    anchors: list[tuple[int, TextBlock]],
    current_anchor: TextBlock,
    column_split_x: float | None,
    page_height: int,
) -> float:
    current_x1, current_y1, _current_x2, _current_y2 = [float(value) for value in current_anchor.coordinates]
    current_column = _resolve_column(current_x1, column_split_x)
    candidate_tops = []
    for _q_num, anchor in anchors:
        x1, y1, _x2, _y2 = [float(value) for value in anchor.coordinates]
        if anchor is current_anchor:
            continue
        if _resolve_column(x1, column_split_x) != current_column:
            continue
        if y1 > current_y1 + 2.0:
            candidate_tops.append(y1)
    if not candidate_tops:
        return float(page_height - 20)
    return min(candidate_tops)


def _column_right_boundary(column: str, column_split_x: float | None, page_width: int) -> float:
    if column == "left" and column_split_x is not None:
        return float(column_split_x)
    return float(page_width)


def _extract_question_metadata(
    detections: list[dict],
    anchor: TextBlock,
    *,
    page_width: int,
    block_bottom: float,
) -> tuple[str, str, list[float] | None]:
    anchor_x1, anchor_y1, anchor_x2, _anchor_y2 = [float(value) for value in anchor.coordinates]
    candidates: list[dict] = []
    inline_prompt = _inline_prompt_from_anchor(anchor)
    if inline_prompt is not None:
        inline_text, inline_bbox = inline_prompt
        candidates.append(
            {
                "text": inline_text,
                "confidence": float(anchor.score or 1.0),
                "bbox": inline_bbox,
            }
        )
    for detection in detections:
        text = str(detection.get("text", "")).strip()
        if not text or text == anchor.text.strip():
            continue
        if parse_question_anchor_text(text) is not None:
            continue
        x1, y1, x2, y2 = [float(value) for value in detection["bbox"]]
        if x1 < anchor_x2 - 2:
            continue
        if x1 > float(page_width) or x2 > float(page_width) + 8.0:
            continue
        if y2 < anchor_y1 - 4.0:
            continue
        if y1 >= float(block_bottom) - 2.0:
            continue
        candidates.append(detection)

    candidates.sort(key=lambda item: (item["bbox"][1], item["bbox"][0]))
    if not candidates:
        return "", "빈줄", None

    option_candidates = [item for item in candidates if _is_option_line(str(item.get("text", "")).strip())]
    option_top = min((float(item["bbox"][1]) for item in option_candidates), default=float("inf"))
    prompt_candidates = [
        item
        for item in candidates
        if not _is_score_tag(str(item.get("text", "")).strip())
        and not _is_option_line(str(item.get("text", "")).strip())
        and float(item["bbox"][1]) < option_top - 2.0
    ]
    if not prompt_candidates:
        prompt_candidates = [
            item for item in candidates if not _is_score_tag(str(item.get("text", "")).strip())
        ]
    if not prompt_candidates:
        return "", "빈줄", None

    lead = prompt_candidates[0]
    lead_text = str(lead.get("text", "")).strip()
    x1, y1, x2, y2 = _union_detection_bboxes(prompt_candidates)
    marker_text = " ".join(str(item.get("text", "")).strip() for item in prompt_candidates[:3])
    return (
        lead_text[:40],
        _infer_answer_marker_type(marker_text or lead_text),
        [
            max(anchor_x2, float(x1)),
            max(0.0, float(y1)),
            min(float(page_width - 1), float(x2)),
            max(float(y1) + 1.0, float(y2)),
        ],
    )


def _inline_prompt_from_anchor(anchor: TextBlock) -> tuple[str, list[float]] | None:
    text = str(anchor.text or "").strip()
    inline_text = re.sub(r"^(?:문항\s*)?\d{1,3}\s*[\.:\)]\s*", "", text)
    inline_text = re.sub(r"^\(\d{1,3}\)\s*", "", inline_text)
    inline_text = re.sub(r"^[Qq]\s*\d{1,3}\s*", "", inline_text)
    inline_text = inline_text.strip()
    if not inline_text or inline_text == text:
        return None

    source_x1, source_y1, source_x2, source_y2 = [float(value) for value in anchor.source_coordinates]
    anchor_right = float(anchor.coordinates[2])
    if source_x2 <= anchor_right + 1.0:
        return None

    return (
        inline_text,
        [
            anchor_right,
            source_y1,
            source_x2,
            source_y2,
        ],
    )


def _infer_answer_marker_type(text: str) -> str:
    if "(" in text or ")" in text:
        return "괄호"
    if any(marker in text for marker in ("①", "②", "③", "④", "⑤")):
        return "객관식"
    if "___" in text or "____" in text or "‗" in text:
        return "밑줄"
    return "빈줄"


def _is_option_line(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if stripped[0] in "①②③④⑤":
        return True
    return sum(stripped.count(marker) for marker in "①②③④⑤") >= 2


def _is_score_tag(text: str) -> bool:
    return bool(QUESTION_SCORE_RE.fullmatch(text.strip()))


def _union_detection_bboxes(detections: list[dict]) -> tuple[float, float, float, float]:
    x1 = min(float(item["bbox"][0]) for item in detections)
    y1 = min(float(item["bbox"][1]) for item in detections)
    x2 = max(float(item["bbox"][2]) for item in detections)
    y2 = max(float(item["bbox"][3]) for item in detections)
    return x1, y1, x2, y2


def _normalize_bbox(
    rect: Rectangle,
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
