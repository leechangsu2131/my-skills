import json

from fastapi.testclient import TestClient

import webapp.main as web_main
from webapp.main import _build_batch_view, create_app


def test_batch_overview_rolls_up_submission_review_state(tmp_path, monkeypatch) -> None:
    app = create_app(tmp_path)
    client = TestClient(app)
    monkeypatch.setattr("webapp.main._start_batch_processing", lambda **kwargs: web_main._process_batch(**kwargs))

    answer_key_payload = {
        "exam_title": "Linear Equations",
        "questions": [
            {
                "q_num": 1,
                "type": "descriptive",
                "answer": "",
                "points": 5,
                "rubric": "Explain the steps and justify the result.",
            }
        ],
    }
    student_payload = {
        "student_name": "Choi Hana",
        "answers": [
            {"q_num": 1, "type": "descriptive", "answer": "I solved it in my head.", "confidence": "medium", "page": 1}
        ],
    }

    client.post(
        "/batches",
        files=[
            ("blank_exam", ("blank.pdf", b"%PDF-1.4", "application/pdf")),
            ("answer_key", ("answer_key.json", json.dumps(answer_key_payload), "application/json")),
            ("student_files", ("student.json", json.dumps(student_payload), "application/json")),
        ],
        follow_redirects=True,
    )

    store = app.state.store
    batch = store.list_batches()[0]
    batch_view = _build_batch_view(store, batch)

    assert batch_view["status"] == "needs_review"


def test_batch_with_no_submissions_is_marked_failed_in_view(tmp_path) -> None:
    app = create_app(tmp_path)
    batch = app.state.store.create_batch("Empty Batch")

    batch_view = _build_batch_view(app.state.store, batch)

    assert batch_view["status"] == "failed"
