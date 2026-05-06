from __future__ import annotations

import json
from pathlib import Path
import zipfile

from PIL import Image, ImageDraw, ImageFont

from project_store import ProjectPaths


MARK_COLOR = (220, 38, 38)
PENCIL_COLORS = ((220, 38, 38), (185, 28, 28), (248, 113, 113))
FONT_CANDIDATES = (
    Path("C:/Windows/Fonts/malgunbd.ttf"),
    Path("C:/Windows/Fonts/arialbd.ttf"),
    Path("C:/Windows/Fonts/malgun.ttf"),
)


def _box_to_pixels(box: dict, width: int, height: int) -> tuple[int, int, int, int]:
    left = max(0, int(float(box.get("x", 0)) * width))
    top = max(0, int(float(box.get("y", 0)) * height))
    right = min(width, int((float(box.get("x", 0)) + float(box.get("w", 0))) * width))
    bottom = min(height, int((float(box.get("y", 0)) + float(box.get("h", 0))) * height))
    return left, top, right, bottom


def _expanded_mark_box(
    left: int,
    top: int,
    right: int,
    bottom: int,
    width: int,
    height: int,
) -> tuple[int, int, int, int]:
    box_w = max(1, right - left)
    box_h = max(1, bottom - top)
    pad_x = max(12, int(box_w * 0.22))
    pad_y = max(12, int(box_h * 0.45))
    return (
        max(0, left - pad_x),
        max(0, top - pad_y),
        min(width - 1, right + pad_x),
        min(height - 1, bottom + pad_y),
    )


def _draw_pencil_ellipse(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], width: int) -> None:
    left, top, right, bottom = box
    offsets = ((0, 0), (2, -1), (-2, 2))
    for idx, (dx, dy) in enumerate(offsets):
        draw.ellipse(
            (left + dx, top + dy, right + dx, bottom + dy),
            outline=PENCIL_COLORS[idx % len(PENCIL_COLORS)],
            width=max(2, width - idx),
        )


def _draw_pencil_slash(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], width: int) -> None:
    left, top, right, bottom = box
    lines = (
        (right, top, left, bottom),
        (right - 3, top + 2, left - 3, bottom + 2),
        (right + 3, top - 2, left + 3, bottom - 2),
    )
    for idx, line in enumerate(lines):
        draw.line(line, fill=PENCIL_COLORS[idx % len(PENCIL_COLORS)], width=max(2, width - idx))


def _score_text(submission: dict) -> str:
    student_id = str(submission.get("student_id", "")).strip()
    total_score = int(submission.get("total_score", 0) or 0)
    total_points = int(submission.get("total_points", 0) or 0)
    if total_points:
        return f"{student_id}  {total_score} / {total_points}"
    return student_id


def _load_score_font(image: Image.Image) -> ImageFont.ImageFont:
    size = max(24, min(64, int(image.height * 0.09)))
    for font_path in FONT_CANDIDATES:
        if font_path.exists():
            try:
                return ImageFont.truetype(str(font_path), size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def _draw_score_header(draw: ImageDraw.ImageDraw, image: Image.Image, submission: dict) -> None:
    text = _score_text(submission)
    if not text:
        return
    font = _load_score_font(image)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = max(0, (image.width - text_w) // 2)
    y = max(8, int(image.height * 0.025))
    pad = max(8, int(image.height * 0.018))
    draw.rounded_rectangle(
        (x - pad, y - pad, x + text_w + pad, y + text_h + pad),
        radius=max(6, pad),
        fill=(255, 255, 255),
        outline=MARK_COLOR,
        width=max(3, int(image.height * 0.008)),
    )
    draw.text((x, y), text, fill=MARK_COLOR, font=font)


def _page_files_for_submission(paths: ProjectPaths, submission: dict) -> dict[int, str]:
    files: dict[int, str] = {}
    for page in submission.get("pages", []):
        if isinstance(page, dict) and page.get("aligned_file"):
            files[int(page.get("page", 1))] = str(page["aligned_file"])
    for item in submission.get("items", []):
        if isinstance(item, dict) and item.get("aligned_file"):
            files.setdefault(int(item.get("page", 1)), str(item["aligned_file"]))
    return files


def mark_submission_pages(paths: ProjectPaths, student_id: str) -> list[Path]:
    submission_path = paths.submissions_dir / f"{student_id}.json"
    if not submission_path.exists():
        raise FileNotFoundError(f"Submission not found: {student_id}")

    submission = json.loads(submission_path.read_text(encoding="utf-8"))
    page_files = _page_files_for_submission(paths, submission)
    out_dir = paths.marked_dir / "students" / student_id
    out_dir.mkdir(parents=True, exist_ok=True)

    outputs: list[Path] = []
    sorted_pages = sorted(page_files.items())
    first_page = sorted_pages[0][0] if sorted_pages else None
    for page, aligned_name in sorted_pages:
        image_path = paths.aligned_dir / aligned_name
        if not image_path.exists():
            continue

        image = Image.open(image_path).convert("RGB")
        draw = ImageDraw.Draw(image)
        width, height = image.size
        if page == first_page:
            _draw_score_header(draw, image, submission)

        for item in submission.get("items", []):
            if int(item.get("page", 1)) != page:
                continue
            if item.get("needs_review"):
                continue
            box = item.get("box") or {}
            left, top, right, bottom = _box_to_pixels(box, width, height)
            mark_box = _expanded_mark_box(left, top, right, bottom, width, height)
            stroke = max(5, min(18, int(min(width, height) * 0.014)))
            if item.get("is_correct"):
                _draw_pencil_ellipse(draw, mark_box, stroke)
            else:
                _draw_pencil_slash(draw, mark_box, stroke + 2)

        out_path = out_dir / f"{student_id}_p{page}_marked.png"
        image.save(out_path)
        outputs.append(out_path)

    return outputs


def mark_all_submissions(paths: ProjectPaths) -> dict[str, list[Path]]:
    results: dict[str, list[Path]] = {}
    for submission_path in sorted(paths.submissions_dir.glob("*.json")):
        results[submission_path.stem] = mark_submission_pages(paths, submission_path.stem)
    return results


def build_student_marked_pdf(paths: ProjectPaths, student_id: str) -> Path:
    page_paths = mark_submission_pages(paths, student_id)
    if not page_paths:
        raise FileNotFoundError(f"No marked pages created: {student_id}")

    images = [Image.open(path).convert("RGB") for path in page_paths]
    pdf_path = paths.marked_dir / "students" / student_id / f"{student_id}_marked.pdf"
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    first, rest = images[0], images[1:]
    first.save(pdf_path, "PDF", resolution=300.0, save_all=True, append_images=rest)
    for image in images:
        image.close()
    return pdf_path


def build_all_marked_pdfs_zip(paths: ProjectPaths) -> Path:
    zip_path = paths.marked_dir / "marked_exams_all.zip"
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for submission_path in sorted(paths.submissions_dir.glob("*.json")):
            pdf_path = build_student_marked_pdf(paths, submission_path.stem)
            archive.write(pdf_path, pdf_path.name)
    return zip_path


def build_all_marked_pdf(paths: ProjectPaths) -> Path:
    page_paths: list[Path] = []
    for submission_path in sorted(paths.submissions_dir.glob("*.json")):
        page_paths.extend(mark_submission_pages(paths, submission_path.stem))
    if not page_paths:
        raise FileNotFoundError("No marked pages created")

    images = [Image.open(path).convert("RGB") for path in page_paths]
    pdf_path = paths.marked_dir / "marked_exams_combined.pdf"
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    first, rest = images[0], images[1:]
    first.save(pdf_path, "PDF", resolution=300.0, save_all=True, append_images=rest)
    for image in images:
        image.close()
    return pdf_path
