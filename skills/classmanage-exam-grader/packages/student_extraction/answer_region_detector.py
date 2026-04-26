from __future__ import annotations

from pathlib import Path
from typing import Any

from packages.student_extraction.answer_regions import localize_multiple_choice_answer_bbox


DEFAULT_YOLO_ALIASES = (
    "answer",
    "answer_area",
    "answer_blank",
    "choice_blank",
    "choice_box",
    "choice_answer_region",
    "checkbox",
    "objective_answer",
    "short_answer_line",
    "descriptive_answer_area",
)


class HybridAnswerRegionDetector:
    def __init__(
        self,
        *,
        mode: str = "opencv",
        weights_path: str | None = None,
        confidence: float = 0.25,
        class_aliases: list[str] | tuple[str, ...] | None = None,
    ) -> None:
        self.mode = str(mode or "opencv").strip().lower()
        self.weights_path = str(weights_path or "").strip()
        self.confidence = float(confidence)
        self.class_aliases = tuple(alias.strip().lower() for alias in (class_aliases or DEFAULT_YOLO_ALIASES))
        self._yolo_model = None

        if self.mode in {"hybrid", "yolo", "yolo_first"} and self.weights_path:
            self._yolo_model = self._load_yolo_model()

    def localize_multiple_choice(
        self,
        page: Any,
        *,
        question_bbox: list[float],
        anchor_bbox: list[float],
        fallback_bbox: list[float],
        prompt_bbox: list[float] | None = None,
    ) -> tuple[list[float], str]:
        if self._yolo_model is not None:
            yolo_bbox = self._detect_with_yolo(page, question_bbox=question_bbox)
            if yolo_bbox is not None:
                return yolo_bbox, "yolo_answer_region"

        return localize_multiple_choice_answer_bbox(
            page,
            question_bbox=question_bbox,
            anchor_bbox=anchor_bbox,
            fallback_bbox=fallback_bbox,
            prompt_bbox=prompt_bbox,
        )

    def _load_yolo_model(self) -> Any | None:
        yolo_class = _resolve_yolo_class()
        if yolo_class is None:
            return None

        weights = Path(self.weights_path)
        if not weights.exists():
            return None

        try:
            return yolo_class(str(weights))
        except Exception:
            return None

    def _detect_with_yolo(
        self,
        page: Any,
        *,
        question_bbox: list[float],
    ) -> list[float] | None:
        crop, origin_x, origin_y = _crop_with_origin(page, question_bbox)
        if crop.size == 0:
            return None

        try:
            results = self._yolo_model.predict(
                source=crop,
                conf=self.confidence,
                verbose=False,
                device="cpu",
            )
        except Exception:
            return None

        detections = _extract_yolo_detections(results, class_aliases=self.class_aliases)
        if not detections:
            return None

        best = max(
            detections,
            key=lambda item: (
                float(item["confidence"]),
                float(item["bbox"][2] - item["bbox"][0]) * float(item["bbox"][3] - item["bbox"][1]),
            ),
        )
        x1, y1, x2, y2 = [float(value) for value in best["bbox"]]
        return [origin_x + x1, origin_y + y1, origin_x + x2, origin_y + y2]


def build_answer_region_detector(config: dict[str, Any]) -> HybridAnswerRegionDetector:
    detector_cfg = dict(config.get("answer_region_detector", {}))
    return HybridAnswerRegionDetector(
        mode=str(detector_cfg.get("mode", "opencv")),
        weights_path=str(detector_cfg.get("weights_path", "") or ""),
        confidence=float(detector_cfg.get("confidence", 0.25)),
        class_aliases=detector_cfg.get("class_aliases"),
    )


def _resolve_yolo_class(_unused_repo_path: str | None = None) -> Any | None:
    try:
        from ultralytics import YOLO
    except Exception:
        return None
    return YOLO


def _extract_yolo_detections(results: Any, *, class_aliases: tuple[str, ...]) -> list[dict[str, Any]]:
    detections: list[dict[str, Any]] = []
    if not results:
        return detections

    for result in results:
        boxes = getattr(result, "boxes", None)
        if boxes is None:
            continue
        names = getattr(result, "names", {}) or {}
        xyxy_values = getattr(getattr(boxes, "xyxy", None), "tolist", lambda: [])()
        conf_values = getattr(getattr(boxes, "conf", None), "tolist", lambda: [])()
        cls_values = getattr(getattr(boxes, "cls", None), "tolist", lambda: [])()
        for bbox, confidence, cls_value in zip(xyxy_values, conf_values, cls_values):
            label = str(names.get(int(cls_value), "")).strip().lower()
            if class_aliases and label and label not in class_aliases:
                continue
            detections.append(
                {
                    "bbox": [float(value) for value in bbox],
                    "confidence": float(confidence),
                    "label": label,
                }
            )
    return detections


def _crop_with_origin(page: Any, bbox: list[float]) -> tuple[Any, float, float]:
    x1, y1, x2, y2 = [int(round(float(value))) for value in bbox]
    x1 = max(x1, 0)
    y1 = max(y1, 0)
    x2 = min(max(x2, x1 + 1), page.shape[1])
    y2 = min(max(y2, y1 + 1), page.shape[0])
    return page[y1:y2, x1:x2], float(x1), float(y1)
