import sys
from pathlib import Path
import json


BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))

from project_store import create_project, project_paths  # type: ignore
from submission_store import build_submission_manifest, count_ocr_work_items, run_ocr_for_project  # type: ignore


def test_build_submission_manifest_groups_pages_by_student():
    files = [
        "aligned_exam_stu001_p1.png",
        "aligned_exam_stu001_p2.png",
        "aligned_exam_stu002_p1.png",
    ]

    manifest = build_submission_manifest(files)

    assert list(manifest.keys()) == ["stu001", "stu002"]
    assert manifest["stu001"]["pages"][0]["page"] == 1
    assert manifest["stu001"]["pages"][1]["page"] == 2


def test_run_ocr_for_project_reports_progress(tmp_path):
    project = create_project(tmp_path, {"name": "demo"})
    paths = project_paths(tmp_path / project["slug"])
    crop_dir = paths.crops_dir / "students" / "stu001"
    crop_dir.mkdir(parents=True)
    (crop_dir / "p1_q1.png").write_bytes(b"fake image")

    manifest_path = paths.submissions_dir / "stu001.json"
    manifest_path.write_text(
        json.dumps(
            {
                "student_id": "stu001",
                "items": [
                    {
                        "item_id": "stu001_p1_q1",
                        "student_id": "stu001",
                        "type": "객관식",
                        "crop_path": "students/stu001/p1_q1.png",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    class FakeEngine:
        def read_text(self, image_path):
            return {"candidates": [{"text": "2)", "confidence": 0.91}]}

    events = []

    updated = run_ocr_for_project(paths, FakeEngine(), progress_callback=events.append)

    assert updated == 1
    assert count_ocr_work_items(paths) == 1
    assert events[0]["total"] == 1
    assert events[0]["processed"] == 0
    assert events[-1]["processed"] == 1
    saved = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert saved["items"][0]["recognized_answer"] == "②"
