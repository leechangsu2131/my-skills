from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

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


def align_page_images(template_page: np.ndarray, student_page: np.ndarray) -> AlignmentResult:
    orb = cv2.ORB_create(1500)
    template_keypoints, template_descriptors = orb.detectAndCompute(template_page, None)
    student_keypoints, student_descriptors = orb.detectAndCompute(student_page, None)

    if template_descriptors is None or student_descriptors is None:
        raise ValueError("Unable to find alignment features on one of the pages")

    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = sorted(
        matcher.match(template_descriptors, student_descriptors),
        key=lambda item: item.distance,
    )
    if len(matches) < 8:
        raise ValueError("Not enough feature matches to align the student page")

    best_matches = matches[:40]
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
