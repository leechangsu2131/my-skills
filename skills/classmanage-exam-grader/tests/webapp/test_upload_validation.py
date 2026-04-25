from io import BytesIO
import json

from fastapi.testclient import TestClient

import webapp.main as web_main
from webapp.main import create_app


def test_batch_creation_requires_blank_exam_file(tmp_path) -> None:
    app = create_app(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/batches",
        files=[
            (
                "answer_key",
                (
                    "answer.json",
                    BytesIO(json.dumps({"exam_title": "Quiz", "questions": []}).encode("utf-8")),
                    "application/json",
                ),
            ),
            (
                "student_files",
                (
                    "student.json",
                    BytesIO(json.dumps({"student_name": "Kim", "answers": []}).encode("utf-8")),
                    "application/json",
                ),
            ),
        ],
    )

    assert response.status_code == 400
    assert "blank exam" in response.text.lower()
    assert app.state.store.list_batches() == []


def test_batch_creation_requires_at_least_one_student_file(tmp_path) -> None:
    app = create_app(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/batches",
        files=[
            (
                "blank_exam",
                (
                    "blank.pdf",
                    BytesIO(b"%PDF-1.4"),
                    "application/pdf",
                ),
            ),
            (
                "answer_key",
                (
                    "answer.json",
                    BytesIO(json.dumps({"exam_title": "Quiz", "questions": []}).encode("utf-8")),
                    "application/json",
                ),
            ),
            ("student_files", (" ", BytesIO(b""), "application/octet-stream")),
        ],
    )

    assert response.status_code == 400
    assert "student" in response.text.lower()
    assert app.state.store.list_batches() == []


def test_failed_batch_detail_persists_error_message(tmp_path, monkeypatch) -> None:
    app = create_app(tmp_path)
    client = TestClient(app)

    def boom(_path, *, blank_exam_path, metadata_dir=None, **kwargs):
        raise RuntimeError("student parse failed")

    monkeypatch.setattr(
        "webapp.main._start_batch_processing",
        lambda **kwargs: web_main._process_batch(**kwargs),
    )
    monkeypatch.setattr("webapp.services.batch_runner.parse_student_file_bundle", boom)

    client.post(
        "/batches",
        files=[
            (
                "blank_exam",
                (
                    "blank.pdf",
                    BytesIO(b"%PDF-1.4"),
                    "application/pdf",
                ),
            ),
            (
                "answer_key",
                (
                    "answer.json",
                    BytesIO(json.dumps({"exam_title": "Quiz", "questions": []}).encode("utf-8")),
                    "application/json",
                ),
            ),
            (
                "student_files",
                (
                    "student.json",
                    BytesIO(json.dumps({"student_name": "Kim", "answers": []}).encode("utf-8")),
                    "application/json",
                ),
            ),
        ],
        follow_redirects=True,
    )

    batch = app.state.store.list_batches()[0]
    detail_response = client.get(f"/batches/{batch.id}")

    assert detail_response.status_code == 200
    assert "student parse failed" in detail_response.text
