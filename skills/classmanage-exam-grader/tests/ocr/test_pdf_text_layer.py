from __future__ import annotations

from types import SimpleNamespace

from packages.student_extraction.pdf_text_layer import extract_line_detections_from_pdf_text_layer
from packages.student_extraction.pdf_text_layer import extract_text_from_render_bbox
from packages.student_extraction.pdf_text_layer import has_enough_text_layer_content


class _FakePage:
    def __init__(self, words):
        self._words = words

    def get_text(self, mode):
        assert mode == "words"
        return self._words


class _FakeDoc:
    def __init__(self, pages):
        self._pages = pages

    def __iter__(self):
        return iter(self._pages)

    def __len__(self):
        return len(self._pages)

    def __getitem__(self, idx):
        return self._pages[idx]

    def close(self):
        return None


def test_extract_line_detections_groups_words_per_line(monkeypatch, tmp_path) -> None:
    fake_doc = _FakeDoc(
        [
            _FakePage(
                [
                    (10.0, 10.0, 20.0, 14.0, "1.", 0, 0, 0),
                    (30.0, 10.0, 42.0, 14.0, "정답", 0, 0, 1),
                    (10.0, 20.0, 16.0, 24.0, "2.", 0, 1, 0),
                ]
            )
        ]
    )
    monkeypatch.setattr("packages.student_extraction.pdf_text_layer.fitz.open", lambda *_args, **_kwargs: fake_doc)

    detections = extract_line_detections_from_pdf_text_layer(tmp_path / "dummy.pdf", dpi=72)

    assert 0 in detections
    assert detections[0][0]["text"] == "1. 정답"
    assert detections[0][1]["text"] == "2."


def test_has_enough_text_layer_content_requires_minimum_lines() -> None:
    assert has_enough_text_layer_content({0: [{"text": "1"}] * 4})
    assert not has_enough_text_layer_content({0: [{"text": "1"}] * 2})


def test_extract_text_from_render_bbox_filters_by_overlap(monkeypatch, tmp_path) -> None:
    fake_doc = _FakeDoc(
        [
            _FakePage(
                [
                    (10.0, 10.0, 18.0, 14.0, "A", 0, 0, 0),
                    (50.0, 50.0, 58.0, 54.0, "B", 0, 1, 0),
                ]
            )
        ]
    )
    monkeypatch.setattr("packages.student_extraction.pdf_text_layer.fitz.open", lambda *_args, **_kwargs: fake_doc)

    text = extract_text_from_render_bbox(
        tmp_path / "dummy.pdf",
        page_index=0,
        render_bbox=[10.0, 10.0, 30.0, 20.0],
        dpi=72,
    )

    assert text == "A"
