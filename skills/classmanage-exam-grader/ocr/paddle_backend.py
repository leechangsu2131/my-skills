from __future__ import annotations

import importlib

import cv2
import numpy as np


class PaddleOcrBackend:
    def __init__(self, *, lang: str = "korean", use_angle_cls: bool = True) -> None:
        self.lang = lang
        self.use_angle_cls = use_angle_cls
        self._engine = None

    def _get_engine(self):
        if self._engine is None:
            try:
                module = importlib.import_module("paddleocr")
            except ModuleNotFoundError as exc:
                raise RuntimeError(
                    "PaddleOCR runtime is not installed. Install paddleocr and paddlepaddle before starting the web app."
                ) from exc
            self._engine = module.PaddleOCR(
                lang=self.lang,
                use_angle_cls=self.use_angle_cls,
                show_log=False,
            )
        return self._engine

    def detect_text(self, image: np.ndarray) -> list[dict]:
        rgb_image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB) if image.ndim == 2 else image
        results = self._get_engine().ocr(rgb_image, cls=self.use_angle_cls)
        detections: list[dict] = []
        for line in results[0] if results else []:
            bbox, (text, confidence) = line
            xs = [point[0] for point in bbox]
            ys = [point[1] for point in bbox]
            detections.append(
                {
                    "text": text,
                    "confidence": float(confidence),
                    "bbox": [float(min(xs)), float(min(ys)), float(max(xs)), float(max(ys))],
                }
            )
        return detections
