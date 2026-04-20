from ocr.question_layout import build_question_layout
from ocr.question_layout import parse_question_anchor_text


def test_parse_question_anchor_accepts_common_labels() -> None:
    assert parse_question_anchor_text("(1)") == 1
    assert parse_question_anchor_text("문항 3.") == 3
    assert parse_question_anchor_text("Q 12") == 12
    assert parse_question_anchor_text("not a question") is None


def test_build_question_layout_sorts_question_regions_by_page_then_number() -> None:
    detections_by_page = {
        0: [
            {"text": "2.", "confidence": 0.99, "bbox": [40, 130, 80, 160]},
            {"text": "1.", "confidence": 0.99, "bbox": [40, 40, 80, 70]},
        ]
    }
    page_sizes = {0: (600, 800)}

    layout = build_question_layout(detections_by_page, page_sizes)

    assert [item.q_num for item in layout.items] == [1, 2]
    assert layout.items[0].page_index == 0
    assert layout.items[0].answer_bbox[1] < layout.items[1].answer_bbox[1]
