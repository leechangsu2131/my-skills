from __future__ import annotations

from pathlib import Path
from typing import Any


class OcrEngine:
    def __init__(self, reader: Any | None = None) -> None:
        if reader is not None:
            self._reader = reader
            return

        try:
            from paddleocr import PaddleOCR  # type: ignore
        except ImportError as exc:  # pragma: no cover - depends on environment
            raise RuntimeError("paddleocr is not installed") from exc

        self._reader = _create_paddle_reader(PaddleOCR)

    def read_text(self, image_path: Path) -> dict:
        path = str(image_path)
        if hasattr(self._reader, "predict"):
            result = self._reader.predict(path)
        else:
            result = self._reader.ocr(path)
        return {"candidates": extract_ocr_candidates(result)}


def _create_paddle_reader(factory: Any) -> Any:
    options = {
        "lang": "korean",
        "enable_mkldnn": False,
        "use_doc_orientation_classify": False,
        "use_doc_unwarping": False,
        "use_textline_orientation": False,
    }
    try:
        return factory(**options)
    except (TypeError, ValueError):
        return factory(use_angle_cls=True, lang="korean")


def extract_ocr_candidates(result: Any) -> list[dict]:
    candidates: list[dict] = []
    if not result:
        return candidates

    pages = result if isinstance(result, (list, tuple)) else [result]
    for page in pages:
        page_dict = _as_dict(page)
        if page_dict is not None:
            _append_dict_candidates(candidates, page_dict)

    if candidates:
        return candidates

    for page in pages:
        if not isinstance(page, (list, tuple)):
            continue
        for line in page:
            text_info = _legacy_text_info(line)
            if text_info is None:
                continue
            text, confidence = text_info
            _append_candidate(candidates, text, confidence)

    return candidates


def _as_dict(value: Any) -> dict | None:
    if isinstance(value, dict):
        return value
    for name in ("to_dict", "dict"):
        method = getattr(value, name, None)
        if callable(method):
            converted = method()
            if isinstance(converted, dict):
                return converted
    json_value = getattr(value, "json", None)
    if isinstance(json_value, dict):
        return json_value
    return None


def _append_dict_candidates(candidates: list[dict], data: dict) -> None:
    texts = data.get("rec_texts")
    scores = data.get("rec_scores", [])
    if isinstance(texts, (list, tuple)):
        for index, text in enumerate(texts):
            confidence = (
                scores[index]
                if isinstance(scores, (list, tuple)) and index < len(scores)
                else 0.0
            )
            _append_candidate(candidates, text, confidence)
        return

    if "text" in data:
        _append_candidate(
            candidates,
            data.get("text"),
            data.get("confidence", data.get("score", 0.0)),
        )


def _legacy_text_info(line: Any) -> tuple[Any, Any] | None:
    if not isinstance(line, (list, tuple)) or len(line) < 2:
        return None
    text_info = line[1]
    if not isinstance(text_info, (list, tuple)) or len(text_info) < 2:
        return None
    return text_info[0], text_info[1]


def _append_candidate(candidates: list[dict], text: Any, confidence: Any) -> None:
    normalized_text = str(text or "").strip()
    if not normalized_text:
        return
    try:
        normalized_confidence = float(confidence)
    except (TypeError, ValueError):
        normalized_confidence = 0.0
    candidates.append({"text": normalized_text, "confidence": normalized_confidence})
