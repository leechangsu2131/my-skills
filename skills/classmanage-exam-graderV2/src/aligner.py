"""
Image alignment helpers for student exam sheets.

Primary strategy:
- Downscale template/student scans for matching stability.
- Use tuned ORB features + Lowe's ratio test + RANSAC homography.

Fallback strategy:
- Reuse the older contour-based page-corner warp when ORB cannot lock on.
- As a final fallback, resize the original image to the template size.
"""

from pathlib import Path

import cv2
import numpy as np


ORB_SCALE = 0.25
ORB_MIN_GOOD_MATCHES = 20
ORB_MIN_INLIERS = 30
ORB_MIN_CONFIDENCE = 0.20


def _imread_safe(path: str):
    """Read images safely, including Windows paths with non-ASCII text."""
    arr = np.fromfile(path, np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def _imwrite_safe(path: str, img):
    """Write images safely, including Windows paths with non-ASCII text."""
    ext = Path(path).suffix
    ok, buf = cv2.imencode(ext, img)
    if ok:
        with open(path, "wb") as f:
            buf.tofile(f)


def _order_points(pts: np.ndarray) -> np.ndarray:
    """Return points ordered as top-left, top-right, bottom-right, bottom-left."""
    rect = np.zeros((4, 2), dtype=np.float32)
    sums = pts.sum(axis=1)
    diffs = np.diff(pts, axis=1)
    rect[0] = pts[np.argmin(sums)]
    rect[2] = pts[np.argmax(sums)]
    rect[1] = pts[np.argmin(diffs)]
    rect[3] = pts[np.argmax(diffs)]
    return rect


def _find_doc_corners(img_gray: np.ndarray) -> np.ndarray | None:
    """Try to find a 4-corner exam page outline from a grayscale student image."""
    blurred = cv2.GaussianBlur(img_gray, (7, 7), 0)
    _, binary = cv2.threshold(
        blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    edges = cv2.Canny(binary, 30, 120)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    edges = cv2.dilate(edges, kernel, iterations=1)

    contours, _ = cv2.findContours(
        edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    if not contours:
        return None

    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]
    img_area = img_gray.shape[0] * img_gray.shape[1]

    for cnt in contours:
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        if len(approx) != 4:
            continue
        area = cv2.contourArea(approx)
        if area < img_area * 0.05:
            continue
        return approx.reshape(4, 2).astype(np.float32)

    return None


def _align_with_orb(template: np.ndarray, image: np.ndarray) -> tuple[np.ndarray, float] | None:
    """Align a student image to the template using tuned ORB feature matching."""
    h_tmpl, w_tmpl = template.shape[:2]

    t_small = cv2.resize(template, None, fx=ORB_SCALE, fy=ORB_SCALE)
    i_small = cv2.resize(image, None, fx=ORB_SCALE, fy=ORB_SCALE)

    t_gray = cv2.cvtColor(t_small, cv2.COLOR_BGR2GRAY)
    i_gray = cv2.cvtColor(i_small, cv2.COLOR_BGR2GRAY)

    orb = cv2.ORB_create(
        nfeatures=3000,
        scaleFactor=1.2,
        nlevels=8,
        edgeThreshold=15,
        patchSize=31,
    )

    kp1, des1 = orb.detectAndCompute(t_gray, None)
    kp2, des2 = orb.detectAndCompute(i_gray, None)

    if des1 is None or des2 is None:
        print("[Aligner] ORB descriptor extraction failed")
        return None

    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    matches = matcher.knnMatch(des1, des2, k=2)

    good: list[cv2.DMatch] = []
    for pair in matches:
        if len(pair) < 2:
            continue
        m, n = pair
        if m.distance < 0.75 * n.distance:
            good.append(m)

    print(f"[Aligner] ORB matches: total={len(matches)} good={len(good)}")

    if len(good) < ORB_MIN_GOOD_MATCHES:
        return None

    src_pts = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2) / ORB_SCALE
    dst_pts = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2) / ORB_SCALE

    H, mask = cv2.findHomography(dst_pts, src_pts, cv2.RANSAC, 5.0)
    if H is None or mask is None:
        print("[Aligner] ORB homography failed")
        return None

    inliers = int(mask.sum())
    confidence = round(inliers / len(good), 2)
    print(f"[Aligner] ORB inliers: {inliers}, confidence: {confidence}")

    if inliers < ORB_MIN_INLIERS or confidence < ORB_MIN_CONFIDENCE:
        return None

    aligned = cv2.warpPerspective(
        image,
        H,
        (w_tmpl, h_tmpl),
        flags=cv2.INTER_LINEAR,
        borderValue=(255, 255, 255),
    )
    return aligned, confidence


def _align_with_contours(template: np.ndarray, image: np.ndarray) -> np.ndarray | None:
    """Fallback alignment using the detected page outline."""
    h_tmpl, w_tmpl = template.shape[:2]
    img_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    corners = _find_doc_corners(img_gray)
    if corners is None:
        return None

    src_pts = _order_points(corners)
    dst_pts = np.array(
        [
            [0, 0],
            [w_tmpl - 1, 0],
            [w_tmpl - 1, h_tmpl - 1],
            [0, h_tmpl - 1],
        ],
        dtype=np.float32,
    )

    matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
    return cv2.warpPerspective(
        image,
        matrix,
        (w_tmpl, h_tmpl),
        flags=cv2.INTER_LINEAR,
        borderValue=(255, 255, 255),
    )


def align_image(image_path: str, template_path: str, output_path: str) -> bool:
    """
    Align a student exam sheet to the blank template size/layout.

    Returns True when ORB or contour alignment succeeds.
    Returns False when we have to fall back to a simple resize.
    """
    image = _imread_safe(image_path)
    template = _imread_safe(template_path)

    if image is None:
        print(f"[Aligner] Failed to load student image: {image_path}")
        return False
    if template is None:
        print(f"[Aligner] Failed to load template image: {template_path}")
        return False

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    orb_result = _align_with_orb(template, image)
    if orb_result is not None:
        aligned, confidence = orb_result
        _imwrite_safe(output_path, aligned)
        print(
            f"[Aligner] ORB alignment complete: {Path(image_path).name} "
            f"(confidence={confidence})"
        )
        return True

    contour_aligned = _align_with_contours(template, image)
    if contour_aligned is not None:
        _imwrite_safe(output_path, contour_aligned)
        print(f"[Aligner] Contour fallback alignment complete: {Path(image_path).name}")
        return True

    resized = cv2.resize(image, (template.shape[1], template.shape[0]))
    _imwrite_safe(output_path, resized)
    print(f"[Aligner] Alignment failed, resized only: {Path(image_path).name}")
    return False
