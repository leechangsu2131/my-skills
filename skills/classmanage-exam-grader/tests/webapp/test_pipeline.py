from webapp.services.pipeline import parse_answer_key_file, parse_student_file


def test_pipeline_uses_existing_pdf_engine_for_pdf_inputs(tmp_path, monkeypatch) -> None:
    answer_pdf = tmp_path / "answer.pdf"
    student_pdf = tmp_path / "student.pdf"
    answer_pdf.write_bytes(b"%PDF-1.4")
    student_pdf.write_bytes(b"%PDF-1.4")

    monkeypatch.setattr(
        "webapp.services.pipeline.parse_answer_key_pdf",
        lambda path: {"exam_title": "PDF Quiz", "questions": []},
    )
    monkeypatch.setattr(
        "webapp.services.pipeline.extract_answers",
        lambda path: {"student_name": "Lee Bora", "answers": []},
    )

    assert parse_answer_key_file(answer_pdf)["exam_title"] == "PDF Quiz"
    assert parse_student_file(student_pdf)["student_name"] == "Lee Bora"
