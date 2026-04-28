from __future__ import annotations

from pathlib import Path


class OcrEngine:
    def __init__(self) -> None:
        try:
            from paddleocr import PaddleOCR  # type: ignore
        except ImportError as exc:  # pragma: no cover - depends on environment
            raise RuntimeError("paddleocr is not installed") from exc

        self._reader = PaddleOCR(use_angle_cls=True, lang="korean")

    def read_text(self, image_path: Path) -> dict:
        result = self._reader.ocr(str(image_path))
        texts: list[dict] = []
        lines = result[0] if result else []
        for line in lines:
            if len(line) < 2:
                continue
            text_info = line[1]
            if not isinstance(text_info, (list, tuple)) or len(text_info) < 2:
                continue
            texts.append({"text": text_info[0], "confidence": float(text_info[1])})
        return {"candidates": texts}
