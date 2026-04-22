from __future__ import annotations

import importlib
import os
from typing import Any

import cv2
import numpy as np


class PaddleOcrBackend:
    def __init__(self, *, lang: str = "korean", use_angle_cls: bool = True) -> None:
        self.lang = lang
        self.use_angle_cls = use_angle_cls
        self._engine = None

    def _get_engine(self):
        if self._engine is None:
            os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
            try:
                module = importlib.import_module("paddleocr")
            except ModuleNotFoundError as exc:
                raise RuntimeError(
                    "PaddleOCR runtime is not installed. Install paddleocr and paddlepaddle before starting the web app."
                ) from exc
            try:
                self._engine = module.PaddleOCR(
                    lang=self.lang,
                    use_angle_cls=self.use_angle_cls,
                    enable_mkldnn=False,
                    use_doc_orientation_classify=False,
                    use_doc_unwarping=False,
                )
            except ModuleNotFoundError as exc:
                if exc.name == "paddle":
                    raise RuntimeError(
                        "PaddlePaddle runtime is not installed for this Python. Use the bundled Python 3.11 environment and install paddlepaddle."
                    ) from exc
                raise
            except Exception as exc:
                message = str(exc).strip() or exc.__class__.__name__
                if "No model source is available" in message:
                    raise RuntimeError(
                        "PaddleOCR models could not be downloaded. Install python-certifi-win32 or pre-download the official models into %USERPROFILE%\\.paddlex\\official_models."
                    ) from exc
                raise
        return self._engine

    def detect_text(self, image: np.ndarray) -> list[dict]:
        rgb_image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB) if image.ndim == 2 else image
        results = self._run_ocr(rgb_image)
        normalized_results = self._normalize_results(results)
        detections: list[dict] = []
        for bbox, text, confidence in normalized_results:
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

    def _run_ocr(self, image: np.ndarray) -> Any:
        engine = self._get_engine()
        try:
            return engine.ocr(image, cls=self.use_angle_cls)
        except TypeError as exc:
            if "cls" not in str(exc):
                raise
            return engine.ocr(image)

    def _normalize_results(self, results: Any) -> list[tuple[list[list[float]], str, float]]:
        if not results:
            return []

        first_item = results[0]
        if isinstance(first_item, dict) and "rec_texts" in first_item:
            return self._normalize_v3_result(first_item)
        if hasattr(first_item, "get") and first_item.get("rec_texts") is not None:
            return self._normalize_v3_result(first_item)

        normalized: list[tuple[list[list[float]], str, float]] = []
        for line in first_item:
            bbox, (text, confidence) = line
            normalized.append((bbox, text, float(confidence)))
        return normalized

    def _normalize_v3_result(self, result: Any) -> list[tuple[list[list[float]], str, float]]:
        polygons = list(result.get("rec_polys") or result.get("dt_polys") or [])
        texts = list(result.get("rec_texts") or [])
        scores = list(result.get("rec_scores") or [])
        normalized: list[tuple[list[list[float]], str, float]] = []
        for bbox, text, confidence in zip(polygons, texts, scores):
            normalized.append((bbox, text, float(confidence)))
        return normalized
