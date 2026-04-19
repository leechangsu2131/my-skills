from __future__ import annotations

import json
from pathlib import Path

import fitz

from analysis_merger import merge_analysis
from answer_key_parser import load_answer_key_json, parse_answer_key_pdf
from grader import grade_student, load_config
from ocr_extractor import extract_answers
from pdf_annotator import annotate_pdf
from webapp.schemas import ReviewedSubmission, ReviewItem


def parse_answer_key_file(path: Path) -> dict:
    if path.suffix.lower() == ".json":
        return load_answer_key_json(str(path))
    return parse_answer_key_pdf(str(path))


def parse_student_file(
    path: Path,
    *,
    blank_exam_path: Path | None = None,
    metadata_dir: Path | None = None,
) -> dict:
    if path.suffix.lower() == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    if blank_exam_path is None:
        raise ValueError("blank_exam_path is required for PDF student parsing")
    return extract_answers(
        str(path),
        blank_exam_path=str(blank_exam_path),
        metadata_dir=metadata_dir,
    )


def build_reviewed_submission(student_answers: dict, answer_key: dict) -> ReviewedSubmission:
    graded = grade_student(student_answers, answer_key, load_config())
    merged = merge_analysis(graded)
    confidence_map = {"high": 0.95, "medium": 0.7, "low": 0.35}
    questions_by_q = {
        question["q_num"]: question
        for question in answer_key.get("questions", [])
    }
    answers_by_q = {
        answer["q_num"]: answer
        for answer in student_answers.get("answers", [])
    }

    items: list[ReviewItem] = []
    for detail in merged["details"]:
        question = questions_by_q.get(detail["q_num"], {})
        student_entry = answers_by_q.get(detail["q_num"], {})
        needs_review = bool(student_entry.get("requires_review")) or detail["correct"] is None
        feedback_text = (
            question.get("explanation")
            or question.get("rubric")
            or detail.get("analysis")
            or f"Correct answer: {detail['correct_answer']}"
        )
        items.append(
            ReviewItem(
                q_num=detail["q_num"],
                correct=detail["correct"],
                student_answer=detail["student_answer"],
                correct_answer=detail["correct_answer"],
                points_earned=detail["points_earned"],
                points_possible=detail["points_possible"],
                feedback_text=feedback_text,
                feedback_source="answer_key" if question.get("explanation") or question.get("rubric") else "system",
                feedback_confidence=confidence_map.get(student_entry.get("confidence", "medium"), 0.5),
                review_status="needs_review" if needs_review else "approved",
                page=student_entry.get("page"),
                question_text=question.get("question_text"),
                rubric=question.get("rubric"),
            )
        )

    return ReviewedSubmission(
        student_name=merged["student_name"],
        student_number=merged.get("student_number"),
        exam_title=merged.get("exam_title"),
        total_score=merged["total_score"],
        total_points=merged["total_points"],
        correct_count=merged["correct_count"],
        wrong_count=merged["wrong_count"],
        review_count=merged["review_count"],
        items=items,
    )


def finalize_submission_pdf(source_path: Path, payload: ReviewedSubmission, output_path: Path) -> Path:
    real_source = source_path
    if real_source.suffix.lower() != ".pdf":
        real_source = _build_placeholder_source_pdf(
            output_path.parent.parent / "_generated" / f"{source_path.stem}_source.pdf",
            payload,
        )

    graded_payload = {
        "student_name": payload.student_name,
        "student_number": payload.student_number,
        "exam_title": payload.exam_title,
        "total_score": payload.total_score,
        "total_points": payload.total_points,
        "correct_count": payload.correct_count,
        "wrong_count": payload.wrong_count,
        "review_count": payload.review_count,
        "accuracy": round((payload.correct_count / max(payload.correct_count + payload.wrong_count, 1)) * 100, 1),
        "details": [
            {
                "q_num": item.q_num,
                "correct": item.correct,
                "student_answer": item.student_answer,
                "correct_answer": item.correct_answer,
                "points_earned": item.points_earned,
                "points_possible": item.points_possible,
                "analysis": item.feedback_text,
            }
            for item in payload.items
        ],
    }
    return annotate_pdf(str(real_source), graded_payload, str(output_path), load_config())


def _build_placeholder_source_pdf(path: Path, payload: ReviewedSubmission) -> Path:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), f"Student: {payload.student_name}", fontsize=16)
    page.insert_text((72, 96), f"Score: {payload.total_score}/{payload.total_points}", fontsize=12)
    y_position = 132
    for item in payload.items:
        page.insert_text((72, y_position), f"Q{item.q_num} answer: {item.student_answer or '(blank)'}", fontsize=11)
        y_position += 18
    path.parent.mkdir(parents=True, exist_ok=True)
    document.save(path)
    document.close()
    return path
