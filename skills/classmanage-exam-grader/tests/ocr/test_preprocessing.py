from __future__ import annotations

import cv2
import numpy as np
from PIL import Image

from packages.student_extraction.preprocessing import correct_skew
from packages.student_extraction.preprocessing import correct_translation
from packages.student_extraction.preprocessing import preprocess_student_page


def test_correct_skew_detects_small_rotation() -> None:
    template = np.full((220, 220, 3), 255, dtype=np.uint8)
    cv2.line(template, (30, 60), (190, 60), (0, 0, 0), 3)
    cv2.line(template, (30, 120), (190, 120), (0, 0, 0), 3)
    cv2.putText(template, "1", (32, 112), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (0, 0, 0), 3)

    center = (110, 110)
    rotation = cv2.getRotationMatrix2D(center, 3.2, 1.0)
    rotated = cv2.warpAffine(
        template,
        rotation,
        (220, 220),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255),
    )

    result = correct_skew(Image.fromarray(rotated))

    assert result["corrected"] is True
    assert abs(result["angle_deg"]) >= 2.0


def test_correct_translation_uses_anchor_text_and_updates_detections() -> None:
    image = Image.fromarray(np.full((120, 120, 3), 255, dtype=np.uint8))
    template_detections = [
        {"text": "1.", "confidence": 0.99, "bbox": [12.0, 12.0, 20.0, 20.0]},
        {"text": "2.", "confidence": 0.99, "bbox": [12.0, 38.0, 20.0, 46.0]},
    ]
    student_detections = [
        {"text": "1.", "confidence": 0.99, "bbox": [18.0, 16.0, 26.0, 24.0]},
        {"text": "2.", "confidence": 0.99, "bbox": [18.0, 42.0, 26.0, 50.0]},
    ]

    result = correct_translation(
        image,
        template_detections=template_detections,
        student_detections=student_detections,
    )

    assert result["corrected"] is True
    assert result["anchor_count"] == 2
    assert result["dx_px"] == 6
    assert result["dy_px"] == 4
    assert result["detections"][0]["bbox"] == [12.0, 12.0, 20.0, 20.0]


def test_preprocess_student_page_can_skip_translation_ocr() -> None:
    template_page = np.full((120, 120), 255, dtype=np.uint8)
    student_page = np.full((120, 120), 255, dtype=np.uint8)

    result = preprocess_student_page(
        template_page,
        student_page,
        template_detections=[],
        detect_text=lambda _image: (_ for _ in ()).throw(AssertionError("detect_text should not run")),
        enable_translation_correction=False,
    )

    assert result["page_detections"] == []
    assert result["anchor_count"] == 0
