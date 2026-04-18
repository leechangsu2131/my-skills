import json

from fastapi.testclient import TestClient

from webapp.main import create_app


def test_uploading_json_inputs_creates_batch_and_review_page(tmp_path) -> None:
    app = create_app(tmp_path)
    client = TestClient(app)

    answer_key_payload = {
        "exam_title": "Fractions Unit Quiz",
        "questions": [
            {
                "q_num": 1,
                "type": "multiple_choice",
                "answer": "3",
                "points": 5,
                "explanation": "Use a common denominator before comparing fractions.",
            }
        ],
    }
    student_payload = {
        "student_name": "Kim Minsu",
        "student_number": 7,
        "answers": [
            {"q_num": 1, "type": "multiple_choice", "answer": "2", "confidence": "high", "page": 1}
        ],
    }

    response = client.post(
        "/batches",
        files=[
            ("answer_key", ("answer_key.json", json.dumps(answer_key_payload), "application/json")),
            ("student_files", ("kim.json", json.dumps(student_payload), "application/json")),
        ],
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Fractions Unit Quiz" in response.text
    assert "Kim Minsu" in response.text

    store = app.state.store
    batch = store.list_batches()[0]
    submission = store.list_submissions(batch.id)[0]

    review_response = client.get(f"/submissions/{submission.id}/review")

    assert review_response.status_code == 200
    assert "Use a common denominator" in review_response.text
