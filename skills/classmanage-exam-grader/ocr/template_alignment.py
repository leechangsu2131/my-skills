from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import fitz
import numpy as np


@dataclass(slots=True)
class AlignmentResult:
    matrix: np.ndarray
    score: float
    width: int
    height: int


def render_pdf_pages(pdf_path: Path, dpi: int = 160) -> list[np.ndarray]:
    document = fitz.open(pdf_path)
    matrix = fitz.Matrix(dpi / 72, dpi / 72)
    rendered_pages: list[np.ndarray] = []
    for page in document:
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        image = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(pixmap.height, pixmap.width, pixmap.n)
        rendered_pages.append(cv2.cvtColor(image, cv2.COLOR_RGB2GRAY))
    document.close()
    return rendered_pages


def _homography_from_feature_match(
    template_page: np.ndarray,
    student_page: np.ndarray,
    *,
    detector: Any,
    matcher_norm: int,
    min_matches: int,
    top_k: int,
) -> AlignmentResult:
    template_keypoints, template_descriptors = detector.detectAndCompute(template_page, None)
    student_keypoints, student_descriptors = detector.detectAndCompute(student_page, None)

    if template_descriptors is None or student_descriptors is None:
        raise ValueError("Unable to find alignment features on one of the pages")

    matcher = cv2.BFMatcher(matcher_norm, crossCheck=True)
    matches = sorted(
        matcher.match(template_descriptors, student_descriptors),
        key=lambda item: item.distance,
    )
    if len(matches) < min_matches:
        raise ValueError("Not enough feature matches to align the student page")

    best_matches = matches[:top_k]
    source_points = np.float32([template_keypoints[m.queryIdx].pt for m in best_matches]).reshape(-1, 1, 2)
    destination_points = np.float32([student_keypoints[m.trainIdx].pt for m in best_matches]).reshape(-1, 1, 2)
    matrix, mask = cv2.findHomography(source_points, destination_points, cv2.RANSAC, 5.0)
    if matrix is None:
        raise ValueError("Homography estimation failed")

    inliers = float(mask.sum()) if mask is not None else 0.0
    return AlignmentResult(
        matrix=matrix,
        score=inliers / max(len(best_matches), 1),
        width=student_page.shape[1],
        height=student_page.shape[0],
    )


def align_page_images(template_page: np.ndarray, student_page: np.ndarray) -> AlignmentResult:
    """Align template coordinates to student scan space; ORB first, then AKAZE."""
    try:
        return _homography_from_feature_match(
            template_page,
            student_page,
            detector=cv2.ORB_create(2000),
            matcher_norm=cv2.NORM_HAMMING,
            min_matches=8,
            top_k=48,
        )
    except ValueError:
        return _homography_from_feature_match(
            template_page,
            student_page,
            detector=cv2.AKAZE_create(),
            matcher_norm=cv2.NORM_L2,
            min_matches=8,
            top_k=60,
        )


def transform_bbox(
    bbox: list[float],
    matrix: np.ndarray,
    width: int,
    height: int,
) -> list[float]:
    x1, y1, x2, y2 = bbox
    corners = np.float32(
        [
            [x1, y1],
            [x2, y1],
            [x2, y2],
            [x1, y2],
        ]
    ).reshape(-1, 1, 2)
    transformed = cv2.perspectiveTransform(corners, matrix)
    xs = transformed[:, 0, 0]
    ys = transformed[:, 0, 1]

    projected = [
        float(np.clip(xs.min(), 0, max(width - 1, 0))),
        float(np.clip(ys.min(), 0, max(height - 1, 0))),
        float(np.clip(xs.max(), 0, max(width - 1, 0))),
        float(np.clip(ys.max(), 0, max(height - 1, 0))),
    ]
    return projected
