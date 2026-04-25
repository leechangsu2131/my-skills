from __future__ import annotations

from collections import defaultdict
from typing import Any
from typing import Callable

import cv2
import numpy as np
from PIL import Image

from packages.student_extraction.question_layout import parse_question_anchor_text


def correct_skew(img_pil: Image.Image, max_angle_deg: float = 5.0) -> dict[str, Any]:
    """Use long horizontal lines to deskew lightly rotated scans."""
    rgb_image = np.array(img_pil.convert("RGB"))
    gray = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    min_len = int(gray.shape[1] * 0.30)
    lines = cv2.HoughLinesP(
        edges,
        1,
        np.pi / 180,
        threshold=80,
        minLineLength=min_len,
        maxLineGap=20,
    )
    if lines is None or len(lines) < 3:
        return {"image": img_pil, "angle_deg": 0.0, "corrected": False}

    angles: list[float] = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        if x2 == x1:
            continue
        angle = float(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
        if abs(angle) <= max_angle_deg:
            angles.append(angle)

    if len(angles) < 3:
        return {"image": img_pil, "angle_deg": 0.0, "corrected": False}

    median_angle = float(np.median(angles))
    if abs(median_angle) < 0.3:
        return {"image": img_pil, "angle_deg": median_angle, "corrected": False}

    height, width = gray.shape
    center = (width // 2, height // 2)
    matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)
    rotated = cv2.warpAffine(
        rgb_image,
        matrix,
        (width, height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REPLICATE,
    )
    return {
        "image": Image.fromarray(rotated),
        "angle_deg": median_angle,
        "corrected": True,
    }


def correct_translation(
    img_pil: Image.Image,
    *,
    template_detections: list[dict[str, Any]],
    student_detections: list[dict[str, Any]],
    min_anchor_matches: int = 2,
) -> dict[str, Any]:
    """Shift the student page back into place using shared text anchors."""
    template_positions = _collect_anchor_positions(template_detections)
    student_positions = _collect_anchor_positions(student_detections)
    common_keys = sorted(set(template_positions) & set(student_positions))
    if len(common_keys) < min_anchor_matches:
        return {
            "image": img_pil,
            "dx_px": 0,
            "dy_px": 0,
            "anchor_count": 0,
            "corrected": False,
            "detections": student_detections,
        }

    dx_values: list[float] = []
    dy_values: list[float] = []
    for key in common_keys:
        limit = min(len(template_positions[key]), len(student_positions[key]))
        for index in range(limit):
            template_center = template_positions[key][index]
            student_center = student_positions[key][index]
            dx_values.append(student_center[0] - template_center[0])
            dy_values.append(student_center[1] - template_center[1])

    if not dx_values or not dy_values:
        return {
            "image": img_pil,
            "dx_px": 0,
            "dy_px": 0,
            "anchor_count": 0,
            "corrected": False,
            "detections": student_detections,
        }

    dx_px = int(round(float(np.median(dx_values))))
    dy_px = int(round(float(np.median(dy_values))))
    if abs(dx_px) < 3 and abs(dy_px) < 3:
        return {
            "image": img_pil,
            "dx_px": dx_px,
            "dy_px": dy_px,
            "anchor_count": len(common_keys),
            "corrected": False,
            "detections": student_detections,
        }

    rgb_image = np.array(img_pil.convert("RGB"))
    height, width = rgb_image.shape[:2]
    matrix = np.float32([[1, 0, -dx_px], [0, 1, -dy_px]])
    shifted = cv2.warpAffine(
        rgb_image,
        matrix,
        (width, height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REPLICATE,
    )
    adjusted_detections = [_shift_detection_bbox(item, dx_px, dy_px, width, height) for item in student_detections]
    return {
        "image": Image.fromarray(shifted),
        "dx_px": dx_px,
        "dy_px": dy_px,
        "anchor_count": len(common_keys),
        "corrected": True,
        "detections": adjusted_detections,
    }


def preprocess_student_page(
    template_page: np.ndarray,
    student_page: np.ndarray,
    *,
    template_detections: list[dict[str, Any]],
    detect_text: Callable[[np.ndarray], list[dict[str, Any]]],
    enable_translation_correction: bool = True,
) -> dict[str, Any]:
    """Apply deskew first, then anchor-based translation correction."""
    rgb_page = _to_rgb(student_page)
    skew_result = correct_skew(Image.fromarray(rgb_page))
    deskewed_image = np.array(skew_result["image"].convert("RGB"))
    preprocess_applied: list[str] = []
    if skew_result["corrected"]:
        preprocess_applied.append("deskew")

    if not enable_translation_correction:
        return {
            "image": _to_gray(deskewed_image),
            "skew_angle": float(skew_result["angle_deg"]),
            "shift_dx_px": 0,
            "shift_dy_px": 0,
            "anchor_count": 0,
            "page_detections": [],
            "preprocess_applied": preprocess_applied,
            "template_shape": tuple(int(value) for value in template_page.shape[:2]),
        }

    detections = detect_text(_to_gray(deskewed_image))

    translation_result = correct_translation(
        Image.fromarray(deskewed_image),
        template_detections=template_detections,
        student_detections=detections,
    )
    if translation_result["corrected"]:
        preprocess_applied.append("translation")

    return {
        "image": _to_gray(np.array(translation_result["image"].convert("RGB"))),
        "skew_angle": float(skew_result["angle_deg"]),
        "shift_dx_px": int(translation_result["dx_px"]),
        "shift_dy_px": int(translation_result["dy_px"]),
        "anchor_count": int(translation_result["anchor_count"]),
        "page_detections": translation_result["detections"],
        "preprocess_applied": preprocess_applied,
        "template_shape": tuple(int(value) for value in template_page.shape[:2]),
    }


def _collect_anchor_positions(detections: list[dict[str, Any]]) -> dict[str, list[tuple[float, float]]]:
    anchors: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for detection in detections:
        key = _anchor_key(str(detection.get("text", "")))
        if not key:
            continue
        x1, y1, x2, y2 = [float(value) for value in detection["bbox"]]
        anchors[key].append(((x1 + x2) / 2.0, (y1 + y2) / 2.0))
    for positions in anchors.values():
        positions.sort()
    return anchors


def _anchor_key(text: str) -> str | None:
    q_num = parse_question_anchor_text(text)
    if q_num is not None:
        return f"q:{q_num}"
    compact = "".join(text.split()).lower()
    if 1 <= len(compact) <= 12:
        return f"t:{compact}"
    return None


def _shift_detection_bbox(
    detection: dict[str, Any],
    dx_px: int,
    dy_px: int,
    width: int,
    height: int,
) -> dict[str, Any]:
    x1, y1, x2, y2 = [float(value) for value in detection["bbox"]]
    return {
        **detection,
        "bbox": [
            float(np.clip(x1 - dx_px, 0, max(width - 1, 0))),
            float(np.clip(y1 - dy_px, 0, max(height - 1, 0))),
            float(np.clip(x2 - dx_px, 0, max(width - 1, 0))),
            float(np.clip(y2 - dy_px, 0, max(height - 1, 0))),
        ],
    }


def _to_rgb(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
    return image


def _to_gray(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return image
    return cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
