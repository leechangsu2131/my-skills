import importlib
import os
from types import SimpleNamespace

import numpy as np
import pytest

from ocr.paddle_backend import PaddleOcrBackend


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
