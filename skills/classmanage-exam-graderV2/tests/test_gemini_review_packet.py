import json
import sys
from pathlib import Path

from PIL import Image


BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))

from gemini_review_packet import build_gemini_review_packet_pdf, collect_review_items  # type: ignore
from project_store import create_project, project_paths  # type: ignore


def _make_packet_project(tmp_path: Path):
    project = create_project(tmp_path, {"name": "demo"})
    paths = project_paths(tmp_path / project["slug"])
    crop_dir = paths.crops_dir / "students" / "stu001"
    crop_dir.mkdir(parents=True)
    Image.new("RGB", (180, 70), "white").save(crop_dir / "p1_q1.png")
    Image.new("RGB", (180, 70), "white").save(crop_dir / "p1_q2.png")
    submission = {
        "student_id": "stu001",
        "items": [
            {
                "item_id": "stu001_p1_q1",
                "student_id": "stu001",
                "page": 1,
                "question_number": 1,
                "type": "객관식",
                "crop_path": "students/stu001/p1_q1.png",
                "recognized_answer": "",
                "expected_answer": "②",
                "points_possible": 5,
                "needs_review": True,
                "ocr_confidence": 0.21,
            },
            {
                "item_id": "stu001_p1_q2",
                "student_id": "stu001",
                "page": 1,
                "question_number": 2,
                "type": "단답형",
                "crop_path": "students/stu001/p1_q2.png",
                "recognized_answer": "12",
                "expected_answer": "13",
                "points_possible": 4,
                "needs_review": False,
                "ocr_confidence": 0.91,
            },
        ],
    }
    (paths.submissions_dir / "stu001.json").write_text(
        json.dumps(submission, ensure_ascii=False),
        encoding="utf-8",
    )
    return paths


def test_collect_review_items_defaults_to_needs_review(tmp_path):
    paths = _make_packet_project(tmp_path)

    items = collect_review_items(paths)

    assert [item["item_id"] for item in items] == ["stu001_p1_q1"]
    assert items[0]["crop_file"].exists()


def test_collect_review_items_can_filter_selected_ids(tmp_path):
    paths = _make_packet_project(tmp_path)

    items = collect_review_items(paths, ["stu001_p1_q2"])

    assert [item["item_id"] for item in items] == ["stu001_p1_q2"]


def test_build_gemini_review_packet_pdf_writes_pdf_and_manifest(tmp_path):
    paths = _make_packet_project(tmp_path)
    items = collect_review_items(paths, ["stu001_p1_q1", "stu001_p1_q2"])

    pdf_path = build_gemini_review_packet_pdf(paths, items, packet_name="selected")

    assert pdf_path.name == "selected.pdf"
    assert pdf_path.exists()
    assert pdf_path.read_bytes().startswith(b"%PDF")
    manifest_path = pdf_path.with_suffix(".json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert [row["item_id"] for row in manifest["items"]] == ["stu001_p1_q1", "stu001_p1_q2"]
