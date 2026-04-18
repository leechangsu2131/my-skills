import json

from fastapi.testclient import TestClient

from webapp.main import create_app


def test_teacher_review_edit_persists_feedback_changes(tmp_path) -> None:
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
        f"/submissions/{submission.id}/questions/1",
        data={
            "feedback_text": "Teacher note: isolate the variable first, then check by substitution.",
            "review_status": "approved",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    payload = store.load_payload(submission.payload_path)
    assert payload["items"][0]["feedback_source"] == "teacher"
    assert payload["items"][0]["review_status"] == "approved"
