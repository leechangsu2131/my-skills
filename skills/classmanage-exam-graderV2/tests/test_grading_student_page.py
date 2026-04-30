import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient


BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))

from project_store import create_project, project_paths  # type: ignore


def _make_project(tmp_path):
    import webapp.main as app_module

    project = create_project(tmp_path, {"name": "demo"})
    project_dir = tmp_path / project["slug"]
    paths = project_paths(project_dir)
    crop_dir = paths.crops_dir / "students" / "stu001"
    crop_dir.mkdir(parents=True)
    (crop_dir / "p1_q1.png").write_bytes(b"fake image")
    (paths.submissions_dir / "stu001.json").write_text(
        json.dumps(
            {
                "student_id": "stu001",
                "items": [
                    {
                        "item_id": "stu001_p1_q1",
                        "student_id": "stu001",
                        "page": 1,
                        "question_number": 1,
                        "crop_path": "students/stu001/p1_q1.png",
                        "recognized_answer": "②",
                        "expected_answer": "②",
                        "points_possible": 5,
                        "points_earned": 0,
                        "is_correct": False,
                        "needs_review": True,
                        "ocr_confidence": 0.91,
                    }
                ],
                "total_score": 0,
                "total_points": 5,
                "needs_review_count": 1,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    app_module.CURRENT_PROJECT = project_dir.resolve()
    app_module.SETTINGS = {
        "root_dir": str(tmp_path),
        "last_project": project["slug"],
        "app_version": "2.0",
    }
    return app_module, paths


def test_grading_student_detail_renders_manifest_items(tmp_path):
    app_module, _paths = _make_project(tmp_path)
    client = TestClient(app_module.app)

    response = client.get("/grading/student/stu001")

    assert response.status_code == 200
    assert "stu001" in response.text
    assert "stu001_p1_q1" in response.text
    assert "artifacts/crops/students/stu001/p1_q1.png" in response.text


def test_grading_student_review_post_updates_manifest(tmp_path):
    app_module, paths = _make_project(tmp_path)
    client = TestClient(app_module.app)

    response = client.post(
        "/grading/student/stu001",
        data={
            "recognized_answer__stu001_p1_q1": "②",
            "points_earned__stu001_p1_q1": "5",
            "review_status__stu001_p1_q1": "correct",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    saved = json.loads((paths.submissions_dir / "stu001.json").read_text(encoding="utf-8"))
    item = saved["items"][0]
    assert item["points_earned"] == 5
    assert item["is_correct"] is True
    assert item["needs_review"] is False
    assert saved["total_score"] == 5
    assert saved["needs_review_count"] == 0
