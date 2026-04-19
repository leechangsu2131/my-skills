from webapp.services.pipeline import parse_answer_key_file, parse_student_file
from webapp.services.pipeline import build_reviewed_submission


def test_pipeline_uses_existing_pdf_engine_for_pdf_inputs(tmp_path, monkeypatch) -> None:
    answer_pdf = tmp_path / "answer.pdf"
    blank_pdf = tmp_path / "blank.pdf"
    student_pdf = tmp_path / "student.pdf"
    answer_pdf.write_bytes(b"%PDF-1.4")
    blank_pdf.write_bytes(b"%PDF-1.4")
    student_pdf.write_bytes(b"%PDF-1.4")

    monkeypatch.setattr(
        "webapp.services.pipeline.parse_answer_key_pdf",
        lambda path: {"exam_title": "PDF Quiz", "questions": []},
    )
    monkeypatch.setattr(
        "webapp.services.pipeline.extract_answers",
        lambda path, *, blank_exam_path, metadata_dir=None: {"student_name": "Lee Bora", "answers": []},
    )

    assert parse_answer_key_file(answer_pdf)["exam_title"] == "PDF Quiz"
    assert parse_student_file(student_pdf, blank_exam_path=blank_pdf)["student_name"] == "Lee Bora"


def test_parse_student_file_passes_blank_exam_to_extractor(tmp_path, monkeypatch) -> None:
    blank_pdf = tmp_path / "blank.pdf"
    student_pdf = tmp_path / "student.pdf"
    blank_pdf.write_bytes(b"%PDF-1.4")
    student_pdf.write_bytes(b"%PDF-1.4")

    calls: dict[str, str] = {}

    def fake_extract_answers(path: str, *, blank_exam_path: str, metadata_dir=None):
        calls["path"] = path
        calls["blank_exam_path"] = blank_exam_path
        return {"student_name": "Lee Bora", "answers": []}

    monkeypatch.setattr("webapp.services.pipeline.extract_answers", fake_extract_answers)

    result = parse_student_file(student_pdf, blank_exam_path=blank_pdf)

    assert result["student_name"] == "Lee Bora"
    assert calls == {"path": str(student_pdf), "blank_exam_path": str(blank_pdf)}


def test_low_confidence_answer_defaults_to_review() -> None:
    answer_key = {
        "exam_title": "Quiz",
        "questions": [
            {"q_num": 1, "type": "short_answer", "answer": "12", "points": 5}
        ],
    }
    student_answers = {
        "student_name": "Park",
        "answers": [
            {
                "q_num": 1,
                "type": "short_answer",
                "answer": "12",
                "confidence": "low",
                "requires_review": True,
                "page": 1,
            }
        ],
    }

    reviewed = build_reviewed_submission(student_answers, answer_key)

    assert reviewed.items[0].review_status == "needs_review"


def test_pdf_student_extraction_returns_layout_aware_answers(tmp_path, monkeypatch) -> None:
    blank_pdf = tmp_path / "blank.pdf"
    student_pdf = tmp_path / "student.pdf"
    blank_pdf.write_bytes(b"%PDF-1.4")
    student_pdf.write_bytes(b"%PDF-1.4")

    monkeypatch.setattr(
        "webapp.services.pipeline.extract_answers",
        lambda path, *, blank_exam_path, metadata_dir=None: {
            "student_name": "Moon",
            "answers": [
                {
                    "q_num": 1,
                    "answer": "42",
                    "confidence": "high",
                    "page": 1,
                    "requires_review": False,
                }
            ],
        },
    )

    result = parse_student_file(student_pdf, blank_exam_path=blank_pdf)

    assert result["answers"][0]["answer"] == "42"
