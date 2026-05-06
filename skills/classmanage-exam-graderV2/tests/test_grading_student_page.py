import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image


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
    Image.new("RGB", (180, 70), "white").save(crop_dir / "p1_q1.png")
    Image.new("RGB", (200, 200), "white").save(paths.aligned_dir / "aligned_exam_stu001_p1.png")
    (paths.submissions_dir / "stu001.json").write_text(
        json.dumps(
            {
                "student_id": "stu001",
                "pages": [{"page": 1, "aligned_file": "aligned_exam_stu001_p1.png"}],
                "items": [
                    {
                        "item_id": "stu001_p1_q1",
                        "student_id": "stu001",
                        "page": 1,
                        "question_number": 1,
                        "aligned_file": "aligned_exam_stu001_p1.png",
                        "box": {"x": 0.25, "y": 0.45, "w": 0.25, "h": 0.15},
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
    (paths.json_dir / "regions.json").write_text(
        json.dumps(
            {
                "questions": [
                    {
                        "number": 1,
                        "page": 1,
                        "type": "객관식",
                        "box": {"x": 0.25, "y": 0.45, "w": 0.25, "h": 0.15},
                    }
                ],
                "answers": [
                    {"number": 1, "page": 1, "answer": "②", "points": 5, "type": "객관식"}
                ],
                "total_points": 5,
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
    assert "마킹본 생성" in response.text


def test_dashboard_renders_marked_exam_step(tmp_path):
    app_module, _paths = _make_project(tmp_path)
    client = TestClient(app_module.app)

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "마킹본 만들기" in response.text
    assert "전체 마킹본 생성" in response.text
    assert "전체 통합 PDF" in response.text
    assert "학생별 PDF ZIP" in response.text


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


def test_mark_student_exam_endpoint_writes_marked_page(tmp_path):
    app_module, paths = _make_project(tmp_path)
    client = TestClient(app_module.app)

    response = client.post("/api/grading/mark/stu001")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["pages"] == 1
    assert (paths.marked_dir / "students" / "stu001" / "stu001_p1_marked.png").exists()
    assert (paths.marked_dir / "students" / "stu001" / "stu001_marked.pdf").exists()


def test_marked_download_endpoints_return_pdf_and_zip(tmp_path):
    app_module, _paths = _make_project(tmp_path)
    client = TestClient(app_module.app)

    mark_response = client.post("/api/grading/mark-all")
    assert mark_response.status_code == 200
    assert mark_response.json()["success"] is True

    pdf_response = client.get("/api/grading/marked/stu001/download")
    assert pdf_response.status_code == 200
    assert pdf_response.headers["content-type"].startswith("application/pdf")
    assert pdf_response.content.startswith(b"%PDF")

    zip_response = client.get("/api/grading/marked/all/download")
    assert zip_response.status_code == 200
    assert zip_response.headers["content-type"].startswith("application/zip")
    assert zip_response.content.startswith(b"PK")

    combined_response = client.get("/api/grading/marked/all/pdf")
    assert combined_response.status_code == 200
    assert combined_response.headers["content-type"].startswith("application/pdf")
    assert combined_response.content.startswith(b"%PDF")


def test_marked_status_lists_student_outputs(tmp_path):
    app_module, _paths = _make_project(tmp_path)
    client = TestClient(app_module.app)
    client.post("/api/grading/mark/stu001")

    response = client.get("/api/grading/marked/status")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["students"][0]["student_id"] == "stu001"
    assert data["students"][0]["page_count"] == 1
    assert data["students"][0]["pdf_exists"] is True


def test_gemini_review_packet_pdf_endpoint_returns_pdf(tmp_path):
    app_module, _paths = _make_project(tmp_path)
    client = TestClient(app_module.app)

    response = client.post(
        "/api/grading/gemini-review/packet-pdf",
        json={"item_ids": ["stu001_p1_q1"]},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.content.startswith(b"%PDF")


def test_gemini_review_apply_uses_student_id_from_item_id_prefix(tmp_path):
    app_module, paths = _make_project(tmp_path)
    client = TestClient(app_module.app)

    response = client.post(
        "/grading/gemini-review/apply",
        json=[{"item_id": "stu001_p1_q1", "recognized_answer": "③"}],
    )

    assert response.status_code == 200
    assert response.json()["updated"] == 1
    saved = json.loads((paths.submissions_dir / "stu001.json").read_text(encoding="utf-8"))
    item = saved["items"][0]
    assert item["recognized_answer"] == "③"
    assert item["needs_review"] is False


def test_gemini_review_apply_regenerates_existing_marked_pdf(tmp_path):
    app_module, paths = _make_project(tmp_path)
    client = TestClient(app_module.app)

    client.post("/api/grading/mark/stu001")
    original = (paths.marked_dir / "students" / "stu001" / "stu001_p1_marked.png").read_bytes()

    response = client.post(
        "/grading/gemini-review/apply",
        json=[{"item_id": "stu001_p1_q1", "recognized_answer": "②"}],
    )

    assert response.status_code == 200
    assert response.json()["updated"] == 1
    saved = json.loads((paths.submissions_dir / "stu001.json").read_text(encoding="utf-8"))
    assert saved["total_score"] == 5
    regenerated = (paths.marked_dir / "students" / "stu001" / "stu001_p1_marked.png").read_bytes()
    assert regenerated != original


def test_gemini_review_apply_saves_latest_json_for_reload(tmp_path):
    app_module, paths = _make_project(tmp_path)
    client = TestClient(app_module.app)
    payload = [{"item_id": "stu001_p1_q1", "recognized_answer": "②"}]

    response = client.post("/grading/gemini-review/apply", json=payload)

    assert response.status_code == 200
    saved_path = paths.artifacts_dir / "gemini_review" / "gemini_review.json"
    assert saved_path.exists()
    saved = json.loads(saved_path.read_text(encoding="utf-8"))
    assert saved["results"] == payload

    load_response = client.get("/api/grading/gemini-review/latest")
    assert load_response.status_code == 200
    assert load_response.json()["results"] == payload


def test_gemini_review_latest_endpoint_saves_without_applying(tmp_path):
    app_module, paths = _make_project(tmp_path)
    client = TestClient(app_module.app)
    payload = [{"item_id": "stu001_p1_q1", "recognized_answer": "③"}]

    response = client.post("/api/grading/gemini-review/latest", json=payload)

    assert response.status_code == 200
    assert response.json()["count"] == 1
    saved = json.loads((paths.artifacts_dir / "gemini_review" / "gemini_review.json").read_text(encoding="utf-8"))
    assert saved["results"] == payload
    submission = json.loads((paths.submissions_dir / "stu001.json").read_text(encoding="utf-8"))
    assert submission["items"][0]["recognized_answer"] == "②"


def test_mark_all_rescores_before_rendering_marked_outputs(tmp_path):
    app_module, paths = _make_project(tmp_path)
    client = TestClient(app_module.app)

    submission_path = paths.submissions_dir / "stu001.json"
    submission = json.loads(submission_path.read_text(encoding="utf-8"))
    submission["items"][0]["recognized_answer"] = "②"
    submission["items"][0]["is_correct"] = False
    submission["items"][0]["points_earned"] = 0
    submission["items"][0]["needs_review"] = False
    submission["total_score"] = 0
    submission_path.write_text(json.dumps(submission, ensure_ascii=False), encoding="utf-8")

    response = client.post("/api/grading/mark-all")

    assert response.status_code == 200
    assert response.json()["success"] is True
    saved = json.loads(submission_path.read_text(encoding="utf-8"))
    assert saved["total_score"] == 5
    assert (paths.marked_dir / "students" / "stu001" / "stu001_marked.pdf").exists()
