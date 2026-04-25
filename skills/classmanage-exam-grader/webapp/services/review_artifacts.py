from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2

from packages.contracts.models import ReviewedSubmission
from packages.student_extraction.template_alignment import render_pdf_pages


def attach_review_artifacts(
    *,
    submission_id: str,
    payload: ReviewedSubmission,
    blank_exam_path: Path,
    source_pdf_path: Path,
    artifact_dir: Path,
) -> ReviewedSubmission:
    if blank_exam_path.suffix.lower() != ".pdf" or source_pdf_path.suffix.lower() != ".pdf":
        return payload
    if not blank_exam_path.exists() or not source_pdf_path.exists():
        return payload

    review_items = [item for item in payload.items if _should_generate_artifacts(item)]
    if not review_items:
        return payload

    try:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        blank_pages = render_pdf_pages(blank_exam_path)
        student_pages = render_pdf_pages(source_pdf_path)
    except Exception:
        return payload

    updated_items = []
    student_page_urls: dict[int, str] = {}
    reference_page_urls: dict[int, str] = {}
    for item in payload.items:
        if not _should_generate_artifacts(item):
            updated_items.append(item)
            continue

        student_crop_url = None
        reference_crop_url = None
        student_page_url = None
        reference_page_url = None
        student_crop_name = f"q{item.q_num:02d}_student.png"
        reference_crop_name = f"q{item.q_num:02d}_reference.png"

        if item.page and item.page - 1 < len(student_pages):
            page_index = item.page - 1
            student_page_url = _page_artifact_url(
                page_index=page_index,
                page_images=student_pages,
                artifact_dir=artifact_dir,
                url_cache=student_page_urls,
                submission_id=submission_id,
                suffix="student",
            )
            student_crop = _crop_from_bbox(student_pages[page_index], item.review_bbox or item.bbox)
            if student_crop is not None:
                _write_png(artifact_dir / student_crop_name, student_crop)
                student_crop_url = f"/submissions/{submission_id}/artifacts/{student_crop_name}"

        if item.page and item.page - 1 < len(blank_pages):
            page_index = item.page - 1
            reference_page_url = _page_artifact_url(
                page_index=page_index,
                page_images=blank_pages,
                artifact_dir=artifact_dir,
                url_cache=reference_page_urls,
                submission_id=submission_id,
                suffix="reference",
            )
            reference_crop = _crop_from_bbox(blank_pages[page_index], item.template_bbox or item.review_bbox or item.bbox)
            if reference_crop is not None:
                _write_png(artifact_dir / reference_crop_name, reference_crop)
                reference_crop_url = f"/submissions/{submission_id}/artifacts/{reference_crop_name}"

        updated_items.append(
            item.model_copy(
                update={
                    "student_crop_url": student_crop_url or item.student_crop_url,
                    "reference_crop_url": reference_crop_url or item.reference_crop_url,
                    "student_page_url": student_page_url or item.student_page_url,
                    "reference_page_url": reference_page_url or item.reference_page_url,
                }
            )
        )

    return payload.model_copy(update={"items": updated_items})


def _should_generate_artifacts(item: Any) -> bool:
    if item.review_status == "needs_review":
        return True
    if item.review_reason:
        return True
    return item.confidence_score is not None and float(item.confidence_score) < 0.75


def _crop_from_bbox(image: Any, bbox: list[float] | None) -> Any:
    if image is None or bbox is None:
        return None
    x1, y1, x2, y2 = [int(round(float(value))) for value in bbox]
    x1 = max(x1, 0)
    y1 = max(y1, 0)
    x2 = min(max(x2, x1 + 1), image.shape[1])
    y2 = min(max(y2, y1 + 1), image.shape[0])
    crop = image[y1:y2, x1:x2]
    if crop.size == 0:
        return None
    return crop


def _page_artifact_url(
    *,
    page_index: int,
    page_images: list[Any],
    artifact_dir: Path,
    url_cache: dict[int, str],
    submission_id: str,
    suffix: str,
) -> str | None:
    if page_index < 0 or page_index >= len(page_images):
        return None
    cached = url_cache.get(page_index)
    if cached:
        return cached
    artifact_name = f"page{page_index + 1:02d}_{suffix}.png"
    _write_png(artifact_dir / artifact_name, page_images[page_index])
    artifact_url = f"/submissions/{submission_id}/artifacts/{artifact_name}"
    url_cache[page_index] = artifact_url
    return artifact_url


def _write_png(path: Path, image: Any) -> None:
    success, encoded = cv2.imencode(".png", image)
    if not success:
        raise RuntimeError(f"Failed to encode review artifact: {path.name}")
    path.write_bytes(encoded.tobytes())
