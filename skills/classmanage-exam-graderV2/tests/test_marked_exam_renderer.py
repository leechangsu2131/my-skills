import json
import sys
from pathlib import Path

from PIL import Image


BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))

from marked_exam_renderer import (  # type: ignore
    build_all_marked_pdf,
    build_all_marked_pdfs_zip,
    build_student_marked_pdf,
    mark_submission_pages,
)
from project_store import create_project, project_paths  # type: ignore


def _red_pixels_near(image_path: Path, box: tuple[int, int, int, int]) -> int:
    image = Image.open(image_path).convert("RGB")
    left, top, right, bottom = box
    red = 0
    for y in range(top, bottom):
        for x in range(left, right):
            r, g, b = image.getpixel((x, y))
            if r > 180 and g < 100 and b < 100:
                red += 1
    return red


def test_mark_submission_pages_draws_marks_above_answer_boxes(tmp_path):
    project = create_project(tmp_path, {"name": "demo"})
    paths = project_paths(tmp_path / project["slug"])

    aligned = Image.new("RGB", (200, 200), "white")
    aligned.save(paths.aligned_dir / "aligned_exam_stu001_p1.png")

    submission = {
        "student_id": "stu001",
        "pages": [{"page": 1, "aligned_file": "aligned_exam_stu001_p1.png"}],
        "items": [
            {
                "item_id": "stu001_p1_q1",
                "page": 1,
                "question_number": 1,
                "aligned_file": "aligned_exam_stu001_p1.png",
                "box": {"x": 0.25, "y": 0.45, "w": 0.25, "h": 0.15},
                "is_correct": True,
                "needs_review": False,
            },
            {
                "item_id": "stu001_p1_q2",
                "page": 1,
                "question_number": 2,
                "aligned_file": "aligned_exam_stu001_p1.png",
                "box": {"x": 0.55, "y": 0.45, "w": 0.25, "h": 0.15},
                "is_correct": False,
                "needs_review": False,
            },
        ],
    }
    (paths.submissions_dir / "stu001.json").write_text(
        json.dumps(submission, ensure_ascii=False),
        encoding="utf-8",
    )

    outputs = mark_submission_pages(paths, "stu001")

    assert [path.name for path in outputs] == ["stu001_p1_marked.png"]
    assert _red_pixels_near(outputs[0], (42, 80, 108, 128)) > 80
    assert _red_pixels_near(outputs[0], (102, 80, 168, 128)) > 80
    assert _red_pixels_near(outputs[0], (70, 8, 132, 34)) > 5


def test_mark_submission_pages_skips_items_still_needing_review(tmp_path):
    project = create_project(tmp_path, {"name": "demo"})
    paths = project_paths(tmp_path / project["slug"])

    Image.new("RGB", (200, 200), "white").save(paths.aligned_dir / "aligned_exam_stu001_p1.png")
    submission = {
        "student_id": "stu001",
        "pages": [{"page": 1, "aligned_file": "aligned_exam_stu001_p1.png"}],
        "items": [
            {
                "item_id": "stu001_p1_q1",
                "page": 1,
                "question_number": 1,
                "aligned_file": "aligned_exam_stu001_p1.png",
                "box": {"x": 0.25, "y": 0.45, "w": 0.25, "h": 0.15},
                "is_correct": True,
                "needs_review": True,
            }
        ],
    }
    (paths.submissions_dir / "stu001.json").write_text(
        json.dumps(submission, ensure_ascii=False),
        encoding="utf-8",
    )

    outputs = mark_submission_pages(paths, "stu001")

    assert outputs
    assert _red_pixels_near(outputs[0], (42, 80, 108, 128)) == 0


def test_build_student_marked_pdf_writes_student_pdf(tmp_path):
    project = create_project(tmp_path, {"name": "demo"})
    paths = project_paths(tmp_path / project["slug"])

    Image.new("RGB", (200, 200), "white").save(paths.aligned_dir / "aligned_exam_stu001_p1.png")
    submission = {
        "student_id": "stu001",
        "pages": [{"page": 1, "aligned_file": "aligned_exam_stu001_p1.png"}],
        "items": [
            {
                "item_id": "stu001_p1_q1",
                "page": 1,
                "question_number": 1,
                "aligned_file": "aligned_exam_stu001_p1.png",
                "box": {"x": 0.25, "y": 0.45, "w": 0.25, "h": 0.15},
                "is_correct": True,
                "needs_review": False,
                "points_earned": 5,
                "points_possible": 5,
            }
        ],
        "total_score": 5,
        "total_points": 5,
    }
    (paths.submissions_dir / "stu001.json").write_text(
        json.dumps(submission, ensure_ascii=False),
        encoding="utf-8",
    )

    pdf_path = build_student_marked_pdf(paths, "stu001")

    assert pdf_path.name == "stu001_marked.pdf"
    assert pdf_path.exists()
    assert pdf_path.read_bytes().startswith(b"%PDF")


def test_build_all_marked_pdfs_zip_includes_student_pdfs(tmp_path):
    project = create_project(tmp_path, {"name": "demo"})
    paths = project_paths(tmp_path / project["slug"])

    for student_id in ("stu001", "stu002"):
        Image.new("RGB", (200, 200), "white").save(paths.aligned_dir / f"aligned_exam_{student_id}_p1.png")
        submission = {
            "student_id": student_id,
            "pages": [{"page": 1, "aligned_file": f"aligned_exam_{student_id}_p1.png"}],
            "items": [
                {
                    "item_id": f"{student_id}_p1_q1",
                    "page": 1,
                    "question_number": 1,
                    "aligned_file": f"aligned_exam_{student_id}_p1.png",
                    "box": {"x": 0.25, "y": 0.45, "w": 0.25, "h": 0.15},
                    "is_correct": True,
                    "needs_review": False,
                    "points_earned": 5,
                    "points_possible": 5,
                }
            ],
            "total_score": 5,
            "total_points": 5,
        }
        (paths.submissions_dir / f"{student_id}.json").write_text(
            json.dumps(submission, ensure_ascii=False),
            encoding="utf-8",
        )

    zip_path = build_all_marked_pdfs_zip(paths)

    assert zip_path.name == "marked_exams_all.zip"
    import zipfile

    with zipfile.ZipFile(zip_path) as archive:
        assert sorted(archive.namelist()) == ["stu001_marked.pdf", "stu002_marked.pdf"]


def test_score_header_is_large_and_only_on_first_page(tmp_path):
    project = create_project(tmp_path, {"name": "demo"})
    paths = project_paths(tmp_path / project["slug"])

    for page in (1, 2):
        Image.new("RGB", (360, 240), "white").save(paths.aligned_dir / f"aligned_exam_stu001_p{page}.png")

    submission = {
        "student_id": "stu001",
        "pages": [
            {"page": 1, "aligned_file": "aligned_exam_stu001_p1.png"},
            {"page": 2, "aligned_file": "aligned_exam_stu001_p2.png"},
        ],
        "items": [
            {
                "item_id": "stu001_p1_q1",
                "page": 1,
                "question_number": 1,
                "aligned_file": "aligned_exam_stu001_p1.png",
                "box": {"x": 0.25, "y": 0.45, "w": 0.25, "h": 0.15},
                "is_correct": True,
                "needs_review": False,
            },
            {
                "item_id": "stu001_p2_q2",
                "page": 2,
                "question_number": 2,
                "aligned_file": "aligned_exam_stu001_p2.png",
                "box": {"x": 0.25, "y": 0.45, "w": 0.25, "h": 0.15},
                "is_correct": True,
                "needs_review": False,
            },
        ],
        "total_score": 87,
        "total_points": 100,
    }
    (paths.submissions_dir / "stu001.json").write_text(
        json.dumps(submission, ensure_ascii=False),
        encoding="utf-8",
    )

    outputs = mark_submission_pages(paths, "stu001")

    assert _red_pixels_near(outputs[0], (120, 8, 240, 58)) > 80
    assert _red_pixels_near(outputs[1], (120, 8, 240, 58)) == 0


def test_build_all_marked_pdf_combines_students_into_one_pdf(tmp_path):
    project = create_project(tmp_path, {"name": "demo"})
    paths = project_paths(tmp_path / project["slug"])

    for student_id in ("stu001", "stu002"):
        Image.new("RGB", (200, 200), "white").save(paths.aligned_dir / f"aligned_exam_{student_id}_p1.png")
        submission = {
            "student_id": student_id,
            "pages": [{"page": 1, "aligned_file": f"aligned_exam_{student_id}_p1.png"}],
            "items": [
                {
                    "item_id": f"{student_id}_p1_q1",
                    "page": 1,
                    "question_number": 1,
                    "aligned_file": f"aligned_exam_{student_id}_p1.png",
                    "box": {"x": 0.25, "y": 0.45, "w": 0.25, "h": 0.15},
                    "is_correct": True,
                    "needs_review": False,
                }
            ],
            "total_score": 5,
            "total_points": 5,
        }
        (paths.submissions_dir / f"{student_id}.json").write_text(
            json.dumps(submission, ensure_ascii=False),
            encoding="utf-8",
        )

    pdf_path = build_all_marked_pdf(paths)

    assert pdf_path.name == "marked_exams_combined.pdf"
    assert pdf_path.exists()
    assert pdf_path.read_bytes().startswith(b"%PDF")
