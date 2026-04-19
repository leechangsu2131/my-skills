from __future__ import annotations

from dataclasses import dataclass
import re


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


def build_question_layout(
    detections_by_page: dict[int, list[dict]],
    page_sizes: dict[int, tuple[int, int]],
) -> QuestionLayout:
    items: list[QuestionRegion] = []

    for page_index, detections in detections_by_page.items():
        anchors: list[tuple[int, list[float]]] = []
        for detection in detections:
            match = QUESTION_RE.match(str(detection["text"]).strip())
            if match:
                anchors.append((int(match.group(1)), detection["bbox"]))

        anchors.sort(key=lambda item: (item[1][1], item[0]))
        page_width, page_height = page_sizes[page_index]
        for index, (q_num, bbox) in enumerate(anchors):
            next_top = anchors[index + 1][1][1] if index + 1 < len(anchors) else page_height - 20
            answer_bbox = [
                bbox[2] + 12,
                max(bbox[1] - 8, 0),
                page_width - 24,
                min(next_top - 8, page_height - 1),
            ]
            items.append(
                QuestionRegion(
                    q_num=q_num,
                    page_index=page_index,
                    anchor_bbox=bbox,
                    answer_bbox=answer_bbox,
                )
            )

    items.sort(key=lambda item: (item.page_index, item.q_num))
    return QuestionLayout(items=items)
