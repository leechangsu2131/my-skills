from __future__ import annotations

import cv2
import numpy as np

from packages.student_extraction.answer_regions import localize_multiple_choice_answer_bbox
from packages.student_extraction.question_layout import QuestionLayout
from packages.student_extraction.question_layout import QuestionRegion
from packages.student_extraction.service import _refine_layout_answer_regions


def test_localize_multiple_choice_answer_bbox_prefers_parenthesized_blank() -> None:
    page = np.full((120, 320), 255, dtype=np.uint8)
    cv2.putText(page, "1.", (12, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.8, 0, 2)
    cv2.putText(page, "QUESTION", (42, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.8, 0, 2)
    cv2.putText(page, "(", (214, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, 0, 2)
    cv2.putText(page, ")", (258, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, 0, 2)

    bbox, marker_type = localize_multiple_choice_answer_bbox(
        page,
        question_bbox=[10.0, 20.0, 300.0, 70.0],
        anchor_bbox=[12.0, 28.0, 26.0, 48.0],
        fallback_bbox=[250.0, 22.0, 294.0, 48.0],
    )

    assert marker_type == "parenthesized_blank"
    assert bbox[0] < 230.0
    assert bbox[2] > 250.0
    assert bbox[3] > 45.0


def test_localize_multiple_choice_answer_bbox_finds_parentheses_inside_wide_prompt_bbox() -> None:
    page = np.full((180, 640), 255, dtype=np.uint8)
    cv2.putText(page, "10.", (14, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.9, 0, 2)
    cv2.putText(page, "QUESTION TEXT", (64, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.9, 0, 2)
    cv2.putText(page, "MORE TEXT", (64, 84), cv2.FONT_HERSHEY_SIMPLEX, 0.9, 0, 2)
    cv2.putText(page, "(", (250, 86), cv2.FONT_HERSHEY_SIMPLEX, 1.0, 0, 2)
    cv2.putText(page, ")", (294, 86), cv2.FONT_HERSHEY_SIMPLEX, 1.0, 0, 2)
    cv2.putText(page, "1", (94, 128), cv2.FONT_HERSHEY_SIMPLEX, 0.9, 0, 2)
    cv2.putText(page, "2", (174, 128), cv2.FONT_HERSHEY_SIMPLEX, 0.9, 0, 2)
    cv2.putText(page, "3", (254, 128), cv2.FONT_HERSHEY_SIMPLEX, 0.9, 0, 2)

    bbox, marker_type = localize_multiple_choice_answer_bbox(
        page,
        question_bbox=[10.0, 20.0, 600.0, 132.0],
        anchor_bbox=[14.0, 30.0, 44.0, 54.0],
        fallback_bbox=[520.0, 22.0, 594.0, 56.0],
    )

    assert marker_type == "parenthesized_blank"
    assert bbox[0] < 266.0
    assert bbox[2] > 286.0
    assert bbox[1] > 55.0


def test_refine_layout_answer_regions_keeps_multiple_choice_prompt_wide_enough_for_blank() -> None:
    page = np.full((180, 640), 255, dtype=np.uint8)
    cv2.putText(page, "10.", (14, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.9, 0, 2)
    cv2.putText(page, "QUESTION TEXT", (64, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.9, 0, 2)
    cv2.putText(page, "MORE TEXT", (64, 84), cv2.FONT_HERSHEY_SIMPLEX, 0.9, 0, 2)
    cv2.putText(page, "(", (360, 86), cv2.FONT_HERSHEY_SIMPLEX, 1.0, 0, 2)
    cv2.putText(page, ")", (404, 86), cv2.FONT_HERSHEY_SIMPLEX, 1.0, 0, 2)
    cv2.putText(page, "1", (94, 128), cv2.FONT_HERSHEY_SIMPLEX, 0.9, 0, 2)
    cv2.putText(page, "2", (174, 128), cv2.FONT_HERSHEY_SIMPLEX, 0.9, 0, 2)
    cv2.putText(page, "3", (254, 128), cv2.FONT_HERSHEY_SIMPLEX, 0.9, 0, 2)

    layout = QuestionLayout(
        items=[
            QuestionRegion(
                q_num=10,
                page_index=0,
                anchor_bbox=[14.0, 30.0, 44.0, 54.0],
                answer_bbox=[70.0, 20.0, 604.0, 140.0],
                question_bbox=[10.0, 20.0, 604.0, 140.0],
            )
        ]
    )

    refined = _refine_layout_answer_regions(layout, [page], {10: "multiple_choice"})
    region = refined.items[0]

    assert region.answer_marker_type == "parenthesized_blank"
    assert region.answer_bbox[0] < 376.0
    assert region.answer_bbox[2] > 396.0
    assert region.question_bbox is not None
    assert region.question_bbox[2] > 500.0


def test_localize_multiple_choice_answer_bbox_handles_thin_wide_parentheses() -> None:
    page = np.full((170, 620), 255, dtype=np.uint8)
    cv2.putText(page, "12.", (14, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.85, 0, 2)
    cv2.putText(page, "PROMPT TEXT", (64, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.85, 0, 2)
    cv2.putText(page, "SECOND LINE", (64, 82), cv2.FONT_HERSHEY_SIMPLEX, 0.85, 0, 2)
    cv2.putText(page, "(", (250, 84), cv2.FONT_HERSHEY_SIMPLEX, 0.7, 0, 1)
    cv2.putText(page, ")", (306, 84), cv2.FONT_HERSHEY_SIMPLEX, 0.7, 0, 1)

    bbox, marker_type = localize_multiple_choice_answer_bbox(
        page,
        question_bbox=[10.0, 20.0, 580.0, 120.0],
        anchor_bbox=[14.0, 30.0, 44.0, 54.0],
        fallback_bbox=[500.0, 22.0, 574.0, 56.0],
    )

    assert marker_type == "parenthesized_blank"
    assert bbox[0] < 266.0
    assert bbox[2] > 296.0


def test_refine_layout_answer_regions_prefers_injected_detector_for_multiple_choice() -> None:
    page = np.full((160, 640), 255, dtype=np.uint8)
    cv2.putText(page, "8.", (14, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.9, 0, 2)
    cv2.putText(page, "QUESTION", (64, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.9, 0, 2)

    class FakeDetector:
        def localize_multiple_choice(self, page, *, question_bbox, anchor_bbox, fallback_bbox):
            return [320.0, 34.0, 372.0, 68.0], "yolo_answer_region"

    layout = QuestionLayout(
        items=[
            QuestionRegion(
                q_num=8,
                page_index=0,
                anchor_bbox=[14.0, 30.0, 44.0, 54.0],
                answer_bbox=[70.0, 20.0, 604.0, 140.0],
                question_bbox=[10.0, 20.0, 604.0, 140.0],
            )
        ]
    )

    refined = _refine_layout_answer_regions(
        layout,
        [page],
        {8: "multiple_choice"},
        answer_region_detector=FakeDetector(),
    )

    region = refined.items[0]
    assert region.answer_marker_type == "yolo_answer_region"
    assert region.answer_bbox == [320.0, 34.0, 372.0, 68.0]


def test_refine_layout_answer_regions_keeps_multiple_choice_bbox_inside_two_column_question_bounds() -> None:
    page = np.full((640, 1000), 255, dtype=np.uint8)
    cv2.putText(page, "10.", (44, 222), cv2.FONT_HERSHEY_SIMPLEX, 0.9, 0, 2)
    cv2.putText(page, "QUESTION TEXT", (120, 222), cv2.FONT_HERSHEY_SIMPLEX, 0.9, 0, 2)
    cv2.putText(page, "14.", (560, 222), cv2.FONT_HERSHEY_SIMPLEX, 0.9, 0, 2)
    cv2.putText(page, "RIGHT COLUMN", (640, 222), cv2.FONT_HERSHEY_SIMPLEX, 0.9, 0, 2)

    layout = QuestionLayout(
        items=[
            QuestionRegion(
                q_num=10,
                page_index=0,
                # Some OCR runs over-extend the anchor box into the question text.
                anchor_bbox=[44.0, 192.0, 274.0, 236.0],
                answer_bbox=[286.0, 188.0, 486.0, 250.0],
                question_bbox=[32.0, 186.0, 492.0, 262.0],
            )
        ]
    )

    refined = _refine_layout_answer_regions(layout, [page], {10: "multiple_choice"})
    region = refined.items[0]

    assert region.question_bbox is not None
    assert region.question_bbox[2] < 520.0
    assert region.answer_bbox[2] < 540.0
