import importlib
import os
from types import SimpleNamespace

import numpy as np
import pytest

from packages.student_extraction.paddle_backend import PaddleOcrBackend


def test_paddle_backend_raises_clear_error_when_runtime_missing(monkeypatch) -> None:
    def fake_import(name: str):
        raise ModuleNotFoundError(name)

    monkeypatch.setattr(importlib, "import_module", fake_import)

    backend = PaddleOcrBackend()
    with pytest.raises(RuntimeError, match="PaddleOCR"):
        backend.detect_text(np.zeros((32, 32), dtype=np.uint8))


def test_paddle_backend_supports_paddleocr_v3_style_results(monkeypatch) -> None:
    calls: dict[str, object] = {}

    class FakeEngine:
        def __init__(self, **kwargs) -> None:
            calls["kwargs"] = kwargs

        def ocr(self, image):
            calls["ocr_called"] = True
            return [
                {
                    "rec_texts": ["42"],
                    "rec_scores": [0.91],
                    "rec_polys": [[[1, 2], [5, 2], [5, 8], [1, 8]]],
                }
            ]

    monkeypatch.delenv("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", raising=False)
    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda name: SimpleNamespace(PaddleOCR=FakeEngine),
    )

    backend = PaddleOcrBackend()
    detections = backend.detect_text(np.zeros((16, 16), dtype=np.uint8))

    assert os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] == "True"
    assert calls["kwargs"] == {
        "lang": "korean",
        "use_angle_cls": True,
        "enable_mkldnn": False,
        "use_doc_orientation_classify": False,
        "use_doc_unwarping": False,
    }
    assert calls["ocr_called"] is True
    assert detections == [
        {
            "text": "42",
            "confidence": 0.91,
            "bbox": [1.0, 2.0, 5.0, 8.0],
        }
    ]


def test_paddle_backend_supports_batched_paddleocr_v3_style_results(monkeypatch) -> None:
    calls: dict[str, object] = {}

    class FakeEngine:
        def __init__(self, **kwargs) -> None:
            calls["kwargs"] = kwargs

        def predict(self, images, use_textline_orientation=None):
            calls["batch_size"] = len(images)
            calls["use_textline_orientation"] = use_textline_orientation
            return [
                {
                    "rec_texts": ["42"],
                    "rec_scores": [0.91],
                    "rec_polys": [[[1, 2], [5, 2], [5, 8], [1, 8]]],
                },
                {
                    "rec_texts": ["17"],
                    "rec_scores": [0.83],
                    "rec_polys": [[[2, 3], [6, 3], [6, 9], [2, 9]]],
                },
            ]

    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda name: SimpleNamespace(PaddleOCR=FakeEngine),
    )

    backend = PaddleOcrBackend()
    detections = backend.detect_text_batch(
        [
            np.zeros((16, 16), dtype=np.uint8),
            np.zeros((16, 16), dtype=np.uint8),
        ]
    )

    assert calls["kwargs"] == {
        "lang": "korean",
        "use_angle_cls": True,
        "enable_mkldnn": False,
        "use_doc_orientation_classify": False,
        "use_doc_unwarping": False,
    }
    assert calls["batch_size"] == 2
    assert calls["use_textline_orientation"] is True
    assert detections == [
        [
            {
                "text": "42",
                "confidence": 0.91,
                "bbox": [1.0, 2.0, 5.0, 8.0],
            }
        ],
        [
            {
                "text": "17",
                "confidence": 0.83,
                "bbox": [2.0, 3.0, 6.0, 9.0],
            }
        ],
    ]
