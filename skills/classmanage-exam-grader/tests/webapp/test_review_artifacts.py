from pathlib import Path

import fitz
from fastapi.testclient import TestClient

from packages.contracts.models import ReviewedSubmission
from packages.contracts.models import ReviewItem
from webapp.main import create_app
from webapp.services.review_artifacts import attach_review_artifacts


def _write_demo_pdf(path: Path, text: str) -> None:
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    page.insert_text((72, 96), text, fontsize=18)
    page.insert_text((72, 148), "1. Compare the expression and write the answer.", fontsize=12)
    page.insert_text((72, 196), "Answer area: 42", fontsize=14)
    path.parent.mkdir(parents=True, exist_ok=True)
    document.save(path)
    document.close()


def _build_reviewed_submission() -> ReviewedSubmission:
    return ReviewedSubmission(
        student_name="Kim Minsu",
        total_score=0,
        total_points=5,
        correct_count=0,
        wrong_count=0,
        review_count=1,
        items=[
            ReviewItem(
                q_num=1,
                correct=None,
                student_answer="4Z",
                correct_answer="42",
                points_earned=0,
                points_possible=5,
                feedback_text="Check the final digits carefully.",
                feedback_source="system",
                feedback_confidence=0.35,
                review_status="needs_review",
                confidence_score=0.41,
                alignment_score=0.52,
                extraction_method="crop_ocr",
                review_reason=["low_ocr_confidence"],
                page=1,
                bbox=[72.0, 180.0, 220.0, 220.0],
                review_bbox=[56.0, 126.0, 320.0, 260.0],
                template_bbox=[56.0, 126.0, 320.0, 260.0],
            )
        ],
    )


def test_attach_review_artifacts_creates_student_and_reference_crops(tmp_path) -> None:
    blank_pdf = tmp_path / "blank.pdf"
    student_pdf = tmp_path / "student.pdf"
    artifact_dir = tmp_path / "artifacts"
    _write_demo_pdf(blank_pdf, "Blank exam")
    _write_demo_pdf(student_pdf, "Student scan")

    payload = _build_reviewed_submission()

    updated = attach_review_artifacts(
        submission_id="sub123",
        payload=payload,
        blank_exam_path=blank_pdf,
        source_pdf_path=student_pdf,
        artifact_dir=artifact_dir,
    )

    item = updated.items[0]
    assert item.student_crop_url == "/submissions/sub123/artifacts/q01_student.png"
    assert item.reference_crop_url == "/submissions/sub123/artifacts/q01_reference.png"
    assert item.student_page_url == "/submissions/sub123/artifacts/page01_student.png"
    assert item.reference_page_url == "/submissions/sub123/artifacts/page01_reference.png"
    assert (artifact_dir / "q01_student.png").exists()
    assert (artifact_dir / "q01_reference.png").exists()
    assert (artifact_dir / "page01_student.png").exists()
    assert (artifact_dir / "page01_reference.png").exists()


def test_submission_review_page_shows_review_comparison_panel(tmp_path) -> None:
    app = create_app(tmp_path)
    client = TestClient(app)
    store = app.state.store

    batch = store.create_batch("Comparison Quiz")
    payload_path = Path(batch.folder) / "reviewed" / "submission.json"
    payload = _build_reviewed_submission().model_copy(
        update={
            "items": [
                _build_reviewed_submission().items[0].model_copy(
                    update={
                        "student_crop_url": "/submissions/sub123/artifacts/q01_student.png",
                        "reference_crop_url": "/submissions/sub123/artifacts/q01_reference.png",
                        "student_page_url": "/submissions/sub123/artifacts/page01_student.png",
                        "reference_page_url": "/submissions/sub123/artifacts/page01_reference.png",
                        "manual_page_review": True,
                    }
                )
            ]
        }
    )
    store.save_payload(payload_path, payload.model_dump(mode="json"))
    submission = store.add_submission(
        batch_id=batch.id,
        student_name="Kim Minsu",
        student_number=None,
        status="needs_review",
        total_score=0,
        total_points=5,
        review_count=1,
        payload_path=payload_path,
        source_pdf_path=tmp_path / "student.pdf",
    )

    response = client.get(f"/submissions/{submission.id}/review")

    assert response.status_code == 200
    assert "/submissions/sub123/artifacts/q01_student.png" in response.text
    assert "/submissions/sub123/artifacts/q01_reference.png" in response.text
    assert "/submissions/sub123/artifacts/page01_student.png" in response.text
    assert "/submissions/sub123/artifacts/page01_reference.png" in response.text
    assert f"/submissions/{submission.id}/source" in response.text
    assert "정답 처리" in response.text
    assert "오답 처리" in response.text


def test_submission_artifact_route_serves_saved_png(tmp_path) -> None:
    app = create_app(tmp_path)
    client = TestClient(app)
    store = app.state.store

    batch = store.create_batch("Artifacts")
    payload_path = Path(batch.folder) / "reviewed" / "submission.json"
    store.save_payload(payload_path, _build_reviewed_submission().model_dump(mode="json"))
    submission = store.add_submission(
        batch_id=batch.id,
        student_name="Kim Minsu",
        student_number=None,
        status="needs_review",
        total_score=0,
        total_points=5,
        review_count=1,
        payload_path=payload_path,
        source_pdf_path=tmp_path / "student.pdf",
    )

    artifact_dir = Path(batch.folder) / "artifacts" / submission.id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / "q01_student.png"
    artifact_path.write_bytes(b"\x89PNG\r\n\x1a\n")

    response = client.get(f"/submissions/{submission.id}/artifacts/q01_student.png")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


def test_submission_source_route_serves_original_pdf(tmp_path) -> None:
    app = create_app(tmp_path)
    client = TestClient(app)
    store = app.state.store

    batch = store.create_batch("Artifacts")
    payload_path = Path(batch.folder) / "reviewed" / "submission.json"
    store.save_payload(payload_path, _build_reviewed_submission().model_dump(mode="json"))
    source_pdf_path = tmp_path / "student.pdf"
    _write_demo_pdf(source_pdf_path, "Student scan")
    submission = store.add_submission(
        batch_id=batch.id,
        student_name="Kim Minsu",
        student_number=None,
        status="needs_review",
        total_score=0,
        total_points=5,
        review_count=1,
        payload_path=payload_path,
        source_pdf_path=source_pdf_path,
    )

    response = client.get(f"/submissions/{submission.id}/source")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
