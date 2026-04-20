import json

from fastapi.testclient import TestClient

from webapp.main import create_app
from webapp.schemas import ReviewedSubmission


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
            ("blank_exam", ("blank.pdf", b"%PDF-1.4", "application/pdf")),
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


def test_one_failed_student_does_not_fail_successful_submissions(tmp_path, monkeypatch) -> None:
    app = create_app(tmp_path)
    client = TestClient(app)

    calls = {"count": 0}

    def fake_parse_student_file(path, *, blank_exam_path, metadata_dir=None, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            return {
                "student_name": "Kim",
                "answers": [{"q_num": 1, "answer": "3", "confidence": "high"}],
            }
        raise RuntimeError("alignment failed")

    monkeypatch.setattr("webapp.main.parse_student_file", fake_parse_student_file)
    monkeypatch.setattr(
        "webapp.main.build_reviewed_submission",
        lambda student_answers, answer_key: ReviewedSubmission(
            student_name=student_answers["student_name"],
            total_score=5,
            total_points=5,
            correct_count=1,
            wrong_count=0,
            review_count=0,
            items=[],
        ),
    )

    response = client.post(
        "/batches",
        files=[
            ("blank_exam", ("blank.pdf", b"%PDF-1.4", "application/pdf")),
            ("answer_key", ("answer.json", json.dumps({"exam_title": "Quiz", "questions": []}), "application/json")),
            ("student_files", ("kim.pdf", b"%PDF-1.4", "application/pdf")),
            ("student_files", ("lee.pdf", b"%PDF-1.4", "application/pdf")),
        ],
        follow_redirects=True,
    )

    batch = app.state.store.list_batches()[0]
    submissions = app.state.store.list_submissions(batch.id)

    assert response.status_code == 200
    assert len(submissions) == 2
    assert {item.status for item in submissions} == {"approved", "failed"}
    assert "alignment failed" in response.text


def test_home_page_mentions_blank_exam_requirement(tmp_path) -> None:
    app = create_app(tmp_path)
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "빈 시험지" in response.text
