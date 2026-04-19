from ocr.question_layout import build_question_layout


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
