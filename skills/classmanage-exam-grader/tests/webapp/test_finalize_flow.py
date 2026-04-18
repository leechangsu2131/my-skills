import json

import fitz
from fastapi.testclient import TestClient

from webapp.main import create_app


def test_review_approve_intent_finalizes_student_pdf(tmp_path) -> None:
    app = create_app(tmp_path)
    client = TestClient(app)

    answer_key_payload = {
        "exam_title": "Linear Equations",
        "questions": [
            {
                "q_num": 1,
                "type": "multiple_choice",
                "answer": "4",
                "points": 5,
                "explanation": "Substitute the value back into the equation.",
            }
        ],
    }
    student_payload = {
        "student_name": "Choi Hana",
        "answers": [
            {"q_num": 1, "type": "multiple_choice", "answer": "2", "confidence": "high", "page": 1}
        ],
    }

    client.post(
        "/batches",
        files=[
            ("answer_key", ("answer_key.json", json.dumps(answer_key_payload), "application/json")),
            ("student_files", ("student.json", json.dumps(student_payload), "application/json")),
        ],
        follow_redirects=True,
    )

    store = app.state.store
    batch = store.list_batches()[0]
    submission = store.list_submissions(batch.id)[0]

    response = client.post(
        f"/submissions/{submission.id}/review",
        data={
            "feedback_1": "Teacher note: isolate the variable first, then check by substitution.",
            "points_earned_1": "0",
            "review_status_1": "approved",
            "intent": "approve",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    updated = store.get_submission(submission.id)
    assert updated.status == "finalized"

    output_files = list((tmp_path / "data" / "web" / "batches" / batch.id / "output").glob("*.pdf"))
    assert len(output_files) == 1

    with fitz.open(output_files[0]) as document:
        assert document.page_count >= 2

    download_response = client.get(f"/submissions/{submission.id}/download")
    assert download_response.status_code == 200
    assert download_response.headers["content-type"] == "application/pdf"
