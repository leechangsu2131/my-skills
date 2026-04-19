import importlib

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
