from packages.student_extraction.question_layout import build_question_layout
from packages.student_extraction.question_layout import parse_question_anchor_text


def test_parse_question_anchor_accepts_common_labels() -> None:
    assert parse_question_anchor_text("(1)") == 1
    assert parse_question_anchor_text("문항 3.") == 3
    assert parse_question_anchor_text("Q 12") == 12
    assert parse_question_anchor_text("3") is None
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


def test_build_question_layout_captures_question_snippet_and_marker_type() -> None:
    detections_by_page = {
        0: [
            {"text": "1.", "confidence": 0.99, "bbox": [20, 40, 40, 60]},
            {"text": "다음 중 알맞은 것은 ( )", "confidence": 0.95, "bbox": [55, 38, 180, 62]},
        ]
    }
    page_sizes = {0: (600, 800)}

    layout = build_question_layout(detections_by_page, page_sizes)

    assert layout.items[0].question_text_snippet.startswith("다음 중")
    assert layout.items[0].answer_marker_type == "괄호"
    assert layout.items[0].question_text_bbox == [55.0, 38.0, 180.0, 62.0]


def test_build_question_layout_limits_answer_bbox_to_same_column() -> None:
    detections_by_page = {
        0: [
            {"text": "1.", "confidence": 0.99, "bbox": [20, 40, 40, 60]},
            {"text": "1. left question", "confidence": 0.95, "bbox": [55, 38, 180, 62]},
            {"text": "5.", "confidence": 0.99, "bbox": [330, 40, 350, 60]},
            {"text": "5. right question", "confidence": 0.95, "bbox": [365, 38, 490, 62]},
            {"text": "2.", "confidence": 0.99, "bbox": [20, 180, 40, 200]},
            {"text": "2. left lower", "confidence": 0.95, "bbox": [55, 178, 170, 202]},
        ]
    }
    page_sizes = {0: (600, 800)}

    layout = build_question_layout(detections_by_page, page_sizes)

    left_q1 = next(item for item in layout.items if item.q_num == 1)
    right_q5 = next(item for item in layout.items if item.q_num == 5)
    assert left_q1.answer_bbox[2] < 400
    assert right_q5.answer_bbox[0] > 300


def test_build_question_layout_prefers_compact_anchor_bbox_when_duplicate_question_labels_exist() -> None:
    detections_by_page = {
        0: [
            {"text": "1.", "confidence": 0.90, "bbox": [20, 40, 35, 58]},
            {"text": "1. left question", "confidence": 0.99, "bbox": [20, 38, 180, 62]},
            {"text": "2.", "confidence": 0.99, "bbox": [20, 180, 35, 198]},
        ]
    }
    page_sizes = {0: (600, 800)}

    layout = build_question_layout(detections_by_page, page_sizes)

    assert layout.items[0].anchor_bbox == [20.0, 40.0, 35.0, 58.0]


def test_build_question_layout_shrinks_long_question_line_anchor_to_prefix_width() -> None:
    detections_by_page = {
        0: [
            {"text": "1. left question", "confidence": 0.95, "bbox": [20, 40, 180, 62]},
            {"text": "2. lower question", "confidence": 0.95, "bbox": [20, 180, 170, 202]},
        ]
    }
    page_sizes = {0: (600, 800)}

    layout = build_question_layout(detections_by_page, page_sizes)

    assert layout.items[0].anchor_bbox[2] < 60


def test_build_question_layout_keeps_inline_prompt_text_when_anchor_line_contains_full_stem() -> None:
    detections_by_page = {
        0: [
            {"text": "1. choose answer ( )", "confidence": 0.95, "bbox": [20, 40, 180, 62]},
            {"text": "2. next question", "confidence": 0.95, "bbox": [20, 180, 170, 202]},
        ]
    }
    page_sizes = {0: (600, 800)}

    layout = build_question_layout(detections_by_page, page_sizes)

    q1 = next(item for item in layout.items if item.q_num == 1)
    assert q1.question_text_snippet.startswith("choose answer")
    assert q1.answer_marker_type == "괄호"
    assert q1.question_text_bbox is not None
    assert q1.question_text_bbox[0] >= q1.anchor_bbox[2]


def test_build_question_layout_prefers_real_question_anchor_over_top_header_title() -> None:
    detections_by_page = {
        0: [
            {"text": "2.평면도형", "confidence": 0.98, "bbox": [90, 20, 180, 40]},
            {"text": "1. 다음 중 알맞은 것을 고르시오 (   )", "confidence": 0.91, "bbox": [20, 80, 260, 100]},
            {"text": "2. 다음 중 바르게 설명한 것을 고르시오 (   )", "confidence": 0.62, "bbox": [20, 140, 300, 160]},
            {"text": "3. 다음 중 알맞은 것을 고르시오 (   )", "confidence": 0.91, "bbox": [20, 200, 260, 220]},
        ]
    }
    page_sizes = {0: (600, 800)}

    layout = build_question_layout(detections_by_page, page_sizes)

    q2 = next(item for item in layout.items if item.q_num == 2)
    assert q2.anchor_bbox[1] >= 140.0


def test_build_question_layout_merges_multiline_prompt_and_excludes_score_and_options() -> None:
    detections_by_page = {
        0: [
            {"text": "※ 다음 글을 읽고 물음에 답하시오. (1~2)", "confidence": 0.97, "bbox": [20, 10, 280, 30]},
            {"text": "1.", "confidence": 0.99, "bbox": [20, 40, 38, 60]},
            {"text": "다음 중 옳은 것을 고르시오.", "confidence": 0.96, "bbox": [56, 38, 220, 60]},
            {"text": "조건을 모두 만족하는 것은?", "confidence": 0.96, "bbox": [56, 66, 246, 88]},
            {"text": "[5점]", "confidence": 0.94, "bbox": [258, 38, 304, 60]},
            {"text": "① 첫째 보기", "confidence": 0.92, "bbox": [56, 96, 156, 118]},
            {"text": "② 둘째 보기", "confidence": 0.92, "bbox": [180, 96, 286, 118]},
            {"text": "2.", "confidence": 0.99, "bbox": [20, 160, 38, 180]},
        ]
    }
    page_sizes = {0: (600, 800)}

    layout = build_question_layout(detections_by_page, page_sizes)

    q1 = next(item for item in layout.items if item.q_num == 1)
    assert q1.question_text_snippet == "다음 중 옳은 것을 고르시오."
    assert q1.question_text_bbox == [56.0, 38.0, 246.0, 88.0]


def test_build_question_layout_does_not_treat_plain_option_digits_as_question_anchors() -> None:
    detections_by_page = {
        0: [
            {"text": "1.", "confidence": 0.99, "bbox": [20, 40, 38, 60]},
            {"text": "left prompt", "confidence": 0.95, "bbox": [56, 38, 260, 62]},
            {"text": "2", "confidence": 0.92, "bbox": [60, 140, 78, 160]},
            {"text": "3", "confidence": 0.92, "bbox": [60, 220, 78, 240]},
            {"text": "4", "confidence": 0.92, "bbox": [60, 300, 78, 320]},
            {"text": "5", "confidence": 0.92, "bbox": [60, 380, 78, 400]},
            {"text": "2.", "confidence": 0.99, "bbox": [20, 520, 38, 540]},
            {"text": "next prompt", "confidence": 0.95, "bbox": [56, 518, 180, 542]},
        ]
    }
    page_sizes = {0: (600, 900)}

    layout = build_question_layout(detections_by_page, page_sizes)

    assert [item.q_num for item in layout.items] == [1, 2]
