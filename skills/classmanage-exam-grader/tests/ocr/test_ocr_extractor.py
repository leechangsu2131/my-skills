from types import SimpleNamespace

import numpy as np

from packages.student_extraction.service import extract_answers


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
