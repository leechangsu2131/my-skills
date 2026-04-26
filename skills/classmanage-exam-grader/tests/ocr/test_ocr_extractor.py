from types import SimpleNamespace

import numpy as np

from packages.student_extraction.service import extract_answers
from packages.student_extraction.service import _infer_expected_page_ranges
from packages.student_extraction.service import _refine_layout_answer_regions
from packages.student_extraction.service import _answer_shape_review_reasons


def test_extract_answers_aligns_each_page_once_and_reuses_projection(tmp_path, monkeypatch) -> None:
    blank_pdf = tmp_path / "blank.pdf"
    student_pdf = tmp_path / "student.pdf"
    blank_pdf.write_bytes(b"%PDF-1.4")
    student_pdf.write_bytes(b"%PDF-1.4")

    blank_page = np.full((80, 80), 255, dtype=np.uint8)
    student_page = np.full((80, 80), 255, dtype=np.uint8)

    def fake_render_pdf_pages(path, dpi=160):
        if str(path) == str(blank_pdf):
            return [blank_page]
        return [student_page]

    class FakeBackend:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def detect_text(self, image):
            if image.shape == blank_page.shape:
                return [{"text": "1.", "confidence": 0.99, "bbox": [5, 5, 15, 15]}]
            return [{"text": "42", "confidence": 0.91, "bbox": [0, 0, 10, 10]}]

    regions = [
        SimpleNamespace(q_num=1, page_index=0, anchor_bbox=[5, 5, 15, 15], answer_bbox=[10, 10, 20, 20]),
        SimpleNamespace(q_num=2, page_index=0, anchor_bbox=[5, 25, 15, 35], answer_bbox=[30, 10, 40, 20]),
    ]

    align_calls = {"count": 0}

    def fake_align_page_images(blank, student):
        align_calls["count"] += 1
        return SimpleNamespace(
            matrix=np.array([[1.0, 0.0, 5.0], [0.0, 1.0, 7.0], [0.0, 0.0, 1.0]]),
            score=1.0,
            width=80,
            height=80,
        )

    monkeypatch.setattr("packages.student_extraction.service.load_config", lambda: {})
    monkeypatch.setattr("packages.student_extraction.service.render_pdf_pages", fake_render_pdf_pages)
    monkeypatch.setattr("packages.student_extraction.service.PaddleOcrBackend", FakeBackend)
    monkeypatch.setattr(
        "packages.student_extraction.service.extract_line_detections_from_pdf_text_layer",
        lambda *_args, **_kwargs: {},
    )
    monkeypatch.setattr("packages.student_extraction.service.has_enough_text_layer_content", lambda *_args, **_kwargs: False)
    monkeypatch.setattr("packages.student_extraction.service.extract_text_from_render_bbox", lambda *_args, **_kwargs: "")
    monkeypatch.setattr(
        "packages.student_extraction.service.build_question_layout",
        lambda detections_by_page, page_sizes: SimpleNamespace(items=regions),
    )
    monkeypatch.setattr("packages.student_extraction.service.align_page_images", fake_align_page_images)

    result = extract_answers(str(student_pdf), blank_exam_path=str(blank_pdf))

    assert align_calls["count"] == 1
    assert [item["bbox"] for item in result["answers"]] == [
        [15.0, 17.0, 25.0, 27.0],
        [35.0, 17.0, 45.0, 27.0],
    ]


def test_extract_answers_uses_page_fallback_and_records_review_metadata(tmp_path, monkeypatch) -> None:
    blank_pdf = tmp_path / "blank.pdf"
    student_pdf = tmp_path / "student.pdf"
    blank_pdf.write_bytes(b"%PDF-1.4")
    student_pdf.write_bytes(b"%PDF-1.4")

    blank_page = np.full((80, 80), 255, dtype=np.uint8)
    student_page = np.full((80, 80), 255, dtype=np.uint8)
    highres_page = np.full((160, 160), 255, dtype=np.uint8)

    def fake_render_pdf_pages(path, dpi=160):
        if str(path) == str(blank_pdf):
            return [blank_page]
        if dpi >= 300:
            return [highres_page]
        return [student_page]

    class FakeBackend:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def detect_text(self, image):
            height, width = image.shape[:2]
            if (height, width) == (80, 80):
                return [
                    {"text": "1.", "confidence": 0.99, "bbox": [5, 5, 12, 12]},
                    {"text": "2.", "confidence": 0.99, "bbox": [5, 25, 12, 32]},
                    {"text": "4", "confidence": 0.88, "bbox": [24, 24, 34, 34]},
                ]
            return []

    region = SimpleNamespace(
        q_num=1,
        page_index=0,
        anchor_bbox=[5, 5, 12, 12],
        answer_bbox=[20, 20, 40, 40],
        question_text_snippet="다음 중 알맞은 것",
        answer_marker_type="괄호",
        question_text_bbox=[20, 5, 60, 18],
    )

    monkeypatch.setattr(
        "packages.student_extraction.service.load_config",
        lambda: {
            "ocr": {
                "render_dpi": 160,
                "highres_render_dpi": 320,
                "flag_alignment_review_below": 0.35,
            }
        },
    )
    monkeypatch.setattr("packages.student_extraction.service.render_pdf_pages", fake_render_pdf_pages)
    monkeypatch.setattr("packages.student_extraction.service.PaddleOcrBackend", FakeBackend)
    monkeypatch.setattr(
        "packages.student_extraction.service.extract_line_detections_from_pdf_text_layer",
        lambda *_args, **_kwargs: {
            0: [
                {"text": "1.", "confidence": 1.0, "bbox": [5, 5, 12, 12]},
                {"text": "2.", "confidence": 1.0, "bbox": [5, 25, 12, 32]},
                {"text": "다음 중 알맞은 것은 ( )", "confidence": 1.0, "bbox": [20, 5, 60, 18]},
            ]
        },
    )
    monkeypatch.setattr("packages.student_extraction.service.has_enough_text_layer_content", lambda *_args, **_kwargs: True)
    monkeypatch.setattr("packages.student_extraction.service.extract_text_from_render_bbox", lambda *_args, **_kwargs: "")
    monkeypatch.setattr(
        "packages.student_extraction.service.build_question_layout",
        lambda detections_by_page, page_sizes: SimpleNamespace(items=[region]),
    )
    monkeypatch.setattr(
        "packages.student_extraction.service.align_page_images",
        lambda *_args, **_kwargs: SimpleNamespace(
            matrix=np.eye(3),
            score=0.2,
            width=80,
            height=80,
        ),
    )

    result = extract_answers(str(student_pdf), blank_exam_path=str(blank_pdf))

    answer = result["answers"][0]
    assert answer["answer"] == "4"
    assert answer["extraction_method"] == "page_fallback"
    assert answer["confidence_score"] == 0.88
    assert "fallback_used" in answer["review_reason"]
    assert "low_alignment" in answer["review_reason"]
    assert answer["requires_review"] is True
    assert result["ocr_meta"]["page_metrics"][0]["alignment_score"] == 0.2


def test_extract_answers_uses_anchor_strip_layout_detection_for_scanned_blank_pages(tmp_path, monkeypatch) -> None:
    blank_pdf = tmp_path / "blank.pdf"
    student_pdf = tmp_path / "student.pdf"
    blank_pdf.write_bytes(b"%PDF-1.4")
    student_pdf.write_bytes(b"%PDF-1.4")

    blank_page = np.full((90, 120), 255, dtype=np.uint8)
    student_page = np.full((90, 120), 255, dtype=np.uint8)
    detect_shapes: list[tuple[int, int]] = []

    def fake_render_pdf_pages(path, dpi=160):
        if str(path) == str(blank_pdf):
            return [blank_page]
        return [student_page]

    class FakeBackend:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def detect_text(self, image):
            detect_shapes.append(tuple(image.shape[:2]))
            height, width = image.shape[:2]
            if width <= 50:
                return [{"text": "1. sample prompt", "confidence": 0.99, "bbox": [4, 12, 24, 20]}]
            return [{"text": "42", "confidence": 0.91, "bbox": [0, 0, 10, 10]}]

    monkeypatch.setattr(
        "packages.student_extraction.service.load_config",
        lambda: {
            "ocr": {
                "render_dpi": 160,
                "layout_render_dpi": 50,
                "blank_layout_ocr_mode": "anchor_strips",
                "enable_translation_correction": False,
            }
        },
    )
    monkeypatch.setattr("packages.student_extraction.service.render_pdf_pages", fake_render_pdf_pages)
    monkeypatch.setattr("packages.student_extraction.service.PaddleOcrBackend", FakeBackend)
    monkeypatch.setattr(
        "packages.student_extraction.service.extract_line_detections_from_pdf_text_layer",
        lambda *_args, **_kwargs: {0: []},
    )
    monkeypatch.setattr("packages.student_extraction.service.has_enough_text_layer_content", lambda *_args, **_kwargs: False)
    monkeypatch.setattr("packages.student_extraction.service.extract_text_from_render_bbox", lambda *_args, **_kwargs: "42")
    monkeypatch.setattr(
        "packages.student_extraction.service.align_page_images",
        lambda *_args, **_kwargs: SimpleNamespace(
            matrix=np.eye(3),
            score=1.0,
            width=120,
            height=90,
        ),
    )

    result = extract_answers(str(student_pdf), blank_exam_path=str(blank_pdf))

    assert result["answers"][0]["answer"] == "42"
    assert any(shape[1] < blank_page.shape[1] for shape in detect_shapes)


def test_extract_answers_retries_layout_detection_with_full_page_ocr_when_anchor_coverage_is_sparse(tmp_path, monkeypatch) -> None:
    blank_pdf = tmp_path / "blank.pdf"
    student_pdf = tmp_path / "student.pdf"
    blank_pdf.write_bytes(b"%PDF-1.4")
    student_pdf.write_bytes(b"%PDF-1.4")

    blank_page = np.full((90, 120), 255, dtype=np.uint8)
    student_page = np.full((90, 120), 255, dtype=np.uint8)
    detect_shapes: list[tuple[int, int]] = []

    def fake_render_pdf_pages(path, dpi=160):
        if str(path) == str(blank_pdf):
            return [blank_page]
        return [student_page]

    class FakeBackend:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def detect_text(self, image):
            shape = tuple(image.shape[:2])
            detect_shapes.append(shape)
            height, width = shape
            if width < blank_page.shape[1]:
                return [{"text": "1.", "confidence": 0.99, "bbox": [4, 12, 24, 20]}]
            if shape == tuple(blank_page.shape[:2]):
                return [
                    {"text": "1.", "confidence": 0.99, "bbox": [5, 10, 15, 18]},
                    {"text": "2.", "confidence": 0.99, "bbox": [5, 45, 15, 53]},
                ]
            return []

    monkeypatch.setattr(
        "packages.student_extraction.service.load_config",
        lambda: {
            "ocr": {
                "render_dpi": 160,
                "layout_render_dpi": 50,
                "blank_layout_ocr_mode": "anchor_strips",
                "enable_translation_correction": False,
            }
        },
    )
    monkeypatch.setattr("packages.student_extraction.service.render_pdf_pages", fake_render_pdf_pages)
    monkeypatch.setattr("packages.student_extraction.service.PaddleOcrBackend", FakeBackend)
    monkeypatch.setattr(
        "packages.student_extraction.service.extract_line_detections_from_pdf_text_layer",
        lambda *_args, **_kwargs: {0: []},
    )
    monkeypatch.setattr("packages.student_extraction.service.has_enough_text_layer_content", lambda *_args, **_kwargs: False)
    monkeypatch.setattr("packages.student_extraction.service.extract_text_from_render_bbox", lambda *_args, **_kwargs: "42")
    monkeypatch.setattr(
        "packages.student_extraction.service.align_page_images",
        lambda *_args, **_kwargs: SimpleNamespace(
            matrix=np.eye(3),
            score=1.0,
            width=120,
            height=90,
        ),
    )

    extract_answers(
        str(student_pdf),
        blank_exam_path=str(blank_pdf),
        answer_key={
            "questions": [
                {"q_num": 1, "type": "multiple_choice"},
                {"q_num": 2, "type": "multiple_choice"},
            ]
        },
    )

    assert any(shape[1] < blank_page.shape[1] for shape in detect_shapes)
    assert detect_shapes.count(tuple(blank_page.shape[:2])) >= 1


def test_extract_answers_uses_answer_key_to_fill_missing_regions(tmp_path, monkeypatch) -> None:
    blank_pdf = tmp_path / "blank.pdf"
    student_pdf = tmp_path / "student.pdf"
    blank_pdf.write_bytes(b"%PDF-1.4")
    student_pdf.write_bytes(b"%PDF-1.4")

    blank_page = np.full((120, 120), 255, dtype=np.uint8)
    student_page = np.full((120, 120), 255, dtype=np.uint8)

    def fake_render_pdf_pages(path, dpi=160):
        if str(path) == str(blank_pdf):
            return [blank_page]
        return [student_page]

    class FakeBackend:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def detect_text(self, image):
            return [{"text": "1.", "confidence": 0.99, "bbox": [5, 5, 15, 15]}]

    regions = [
        SimpleNamespace(
            q_num=1,
            page_index=0,
            anchor_bbox=[5, 5, 15, 15],
            answer_bbox=[50, 5, 80, 20],
            question_bbox=[5, 5, 100, 35],
            answer_marker_type="괄호",
            extraction_mode="prompt_choice",
        ),
        SimpleNamespace(
            q_num=3,
            page_index=0,
            anchor_bbox=[5, 65, 15, 75],
            answer_bbox=[50, 65, 80, 80],
            question_bbox=[5, 65, 100, 95],
            answer_marker_type="괄호",
            extraction_mode="prompt_choice",
        ),
    ]

    monkeypatch.setattr("packages.student_extraction.service.load_config", lambda: {"ocr": {"enable_translation_correction": False}})
    monkeypatch.setattr("packages.student_extraction.service.render_pdf_pages", fake_render_pdf_pages)
    monkeypatch.setattr("packages.student_extraction.service.PaddleOcrBackend", FakeBackend)
    monkeypatch.setattr(
        "packages.student_extraction.service.extract_line_detections_from_pdf_text_layer",
        lambda *_args, **_kwargs: {},
    )
    monkeypatch.setattr("packages.student_extraction.service.has_enough_text_layer_content", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(
        "packages.student_extraction.service.build_question_layout",
        lambda *_args, **_kwargs: SimpleNamespace(items=regions),
    )
    monkeypatch.setattr(
        "packages.student_extraction.service.align_page_images",
        lambda *_args, **_kwargs: SimpleNamespace(
            matrix=np.eye(3),
            score=1.0,
            width=120,
            height=120,
        ),
    )
    monkeypatch.setattr(
        "packages.student_extraction.service.extract_text_from_render_bbox",
        lambda *_args, **kwargs: "2" if kwargs.get("render_bbox", [0])[1] < 40 else "4",
    )

    result = extract_answers(
        str(student_pdf),
        blank_exam_path=str(blank_pdf),
        answer_key={
            "questions": [
                {"q_num": 1, "type": "multiple_choice"},
                {"q_num": 2, "type": "multiple_choice"},
                {"q_num": 3, "type": "multiple_choice"},
            ]
        },
    )

    assert [item["q_num"] for item in result["answers"]] == [1, 2, 3]


def test_extract_answers_batches_crop_ocr_requests(tmp_path, monkeypatch) -> None:
    blank_pdf = tmp_path / "blank.pdf"
    student_pdf = tmp_path / "student.pdf"
    blank_pdf.write_bytes(b"%PDF-1.4")
    student_pdf.write_bytes(b"%PDF-1.4")

    blank_page = np.full((80, 80), 255, dtype=np.uint8)
    student_page = np.full((80, 80), 255, dtype=np.uint8)
    batch_calls: list[tuple[tuple[int, int], ...]] = []

    def fake_render_pdf_pages(path, dpi=160):
        if str(path) == str(blank_pdf):
            return [blank_page]
        return [student_page]

    class FakeBackend:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def detect_text(self, image):
            raise AssertionError("crop OCR should be batched")

        def detect_text_batch(self, images):
            batch_calls.append(tuple(tuple(image.shape[:2]) for image in images))
            return [
                [{"text": "12", "confidence": 0.91, "bbox": [0, 0, 10, 10]}],
                [{"text": "34", "confidence": 0.88, "bbox": [0, 0, 10, 10]}],
            ]

    regions = [
        SimpleNamespace(
            q_num=1,
            page_index=0,
            anchor_bbox=[5, 5, 12, 12],
            answer_bbox=[20, 20, 30, 30],
            question_text_snippet="Q1",
            answer_marker_type="blank",
            question_text_bbox=[14, 5, 40, 18],
        ),
        SimpleNamespace(
            q_num=2,
            page_index=0,
            anchor_bbox=[5, 35, 12, 42],
            answer_bbox=[20, 40, 30, 50],
            question_text_snippet="Q2",
            answer_marker_type="blank",
            question_text_bbox=[14, 35, 40, 48],
        ),
    ]

    monkeypatch.setattr(
        "packages.student_extraction.service.load_config",
        lambda: {
            "ocr": {
                "enable_translation_correction": False,
                "render_dpi": 160,
                "highres_render_dpi": 320,
                "flag_alignment_review_below": 0.35,
            }
        },
    )
    monkeypatch.setattr("packages.student_extraction.service.render_pdf_pages", fake_render_pdf_pages)
    monkeypatch.setattr("packages.student_extraction.service.PaddleOcrBackend", FakeBackend)
    monkeypatch.setattr(
        "packages.student_extraction.service.extract_line_detections_from_pdf_text_layer",
        lambda *_args, **_kwargs: {
            0: [
                {"text": "1.", "confidence": 1.0, "bbox": [5, 5, 12, 12]},
                {"text": "2.", "confidence": 1.0, "bbox": [5, 35, 12, 42]},
                {"text": "Q1", "confidence": 1.0, "bbox": [14, 5, 40, 18]},
                {"text": "Q2", "confidence": 1.0, "bbox": [14, 35, 40, 48]},
            ]
        },
    )
    monkeypatch.setattr("packages.student_extraction.service.has_enough_text_layer_content", lambda *_args, **_kwargs: True)
    monkeypatch.setattr("packages.student_extraction.service.extract_text_from_render_bbox", lambda *_args, **_kwargs: "")
    monkeypatch.setattr(
        "packages.student_extraction.service.build_question_layout",
        lambda *_args, **_kwargs: SimpleNamespace(items=regions),
    )
    monkeypatch.setattr(
        "packages.student_extraction.service.align_page_images",
        lambda *_args, **_kwargs: SimpleNamespace(
            matrix=np.eye(3),
            score=1.0,
            width=80,
            height=80,
        ),
    )

    result = extract_answers(str(student_pdf), blank_exam_path=str(blank_pdf))

    assert [item["answer"] for item in result["answers"]] == ["12", "34"]
    assert [item["extraction_method"] for item in result["answers"]] == ["crop_ocr", "crop_ocr"]
    assert batch_calls == [((10, 10), (10, 10))]


def test_refine_layout_answer_regions_detects_answer_line_and_review_only_modes() -> None:
    blank_page = np.full((220, 220), 255, dtype=np.uint8)
    blank_page[116:128, 36:50] = 120
    blank_page[120:123, 55:185] = 0

    line_region = SimpleNamespace(
        q_num=1,
        page_index=0,
        anchor_bbox=[10, 10, 24, 24],
        answer_bbox=[30, 10, 190, 150],
        question_bbox=[10, 10, 200, 150],
        answer_marker_type="빈줄",
        extraction_mode="crop_ocr",
    )
    review_region = SimpleNamespace(
        q_num=2,
        page_index=0,
        anchor_bbox=[10, 160, 24, 174],
        answer_bbox=[30, 160, 190, 210],
        question_bbox=[10, 160, 200, 210],
        answer_marker_type="빈줄",
        extraction_mode="crop_ocr",
    )

    refined = _refine_layout_answer_regions(
        SimpleNamespace(items=[line_region, review_region]),
        [blank_page],
        question_type_by_num={1: "short_answer", 2: "descriptive"},
    )

    assert refined.items[0].extraction_mode == "answer_line"
    assert refined.items[0].answer_bbox[1] >= 108
    assert refined.items[1].extraction_mode == "review_only"


def test_refine_layout_answer_regions_uses_prompt_choice_box_for_multiple_choice_without_answer_line() -> None:
    blank_page = np.full((220, 220), 255, dtype=np.uint8)
    region = SimpleNamespace(
        q_num=1,
        page_index=0,
        anchor_bbox=[10, 10, 24, 24],
        answer_bbox=[30, 10, 190, 90],
        question_bbox=[10, 10, 200, 90],
        answer_marker_type="괄호",
        extraction_mode="crop_ocr",
    )

    refined = _refine_layout_answer_regions(
        SimpleNamespace(items=[region]),
        [blank_page],
        question_type_by_num={1: "multiple_choice"},
    )

    assert refined.items[0].extraction_mode == "prompt_choice"
    assert refined.items[0].answer_bbox[0] >= 120
    assert refined.items[0].answer_bbox[3] <= 55


def test_answer_shape_review_reasons_flags_text_for_multiple_choice() -> None:
    reasons = _answer_shape_review_reasons(
        answer_text="이루는",
        question_spec={"type": "multiple_choice", "answer": "②"},
    )

    assert "answer_shape_mismatch" in reasons


def test_infer_expected_page_ranges_ignores_late_false_low_number() -> None:
    page_items = {
        0: [
            SimpleNamespace(q_num=1),
            SimpleNamespace(q_num=2),
            SimpleNamespace(q_num=3),
            SimpleNamespace(q_num=4),
            SimpleNamespace(q_num=7),
        ],
        1: [
            SimpleNamespace(q_num=9),
            SimpleNamespace(q_num=10),
            SimpleNamespace(q_num=11),
            SimpleNamespace(q_num=14),
            SimpleNamespace(q_num=15),
        ],
        2: [
            SimpleNamespace(q_num=2),
            SimpleNamespace(q_num=19),
            SimpleNamespace(q_num=20),
        ],
    }

    ranges = _infer_expected_page_ranges(page_items, list(range(1, 21)))

    assert ranges == {
        0: (1, 8),
        1: (9, 16),
        2: (17, 20),
    }


def test_answer_shape_review_reasons_flags_latin_text_when_hangul_answer_expected() -> None:
    reasons = _answer_shape_review_reasons(
        answer_text="A",
        question_spec={"type": "short_answer", "answer": "성원"},
    )

    assert "answer_shape_mismatch" in reasons
