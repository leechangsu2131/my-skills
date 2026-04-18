from __future__ import annotations

import json
from pathlib import Path

from analysis_merger import merge_analysis
from answer_key_parser import load_answer_key_json, parse_answer_key_pdf
from grader import grade_student, load_config
from ocr_extractor import extract_answers
from webapp.schemas import ReviewedSubmission, ReviewItem


def parse_answer_key_file(path: Path) -> dict:
    if path.suffix.lower() == ".json":
        return load_answer_key_json(str(path))
    return parse_answer_key_pdf(str(path))


def parse_student_file(path: Path) -> dict:
    if path.suffix.lower() == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    return extract_answers(str(path))


def build_reviewed_submission(student_answers: dict, answer_key: dict) -> ReviewedSubmission:
    graded = grade_student(student_answers, answer_key, load_config())
    merged = merge_analysis(graded)
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
                feedback_confidence=0.95 if question.get("explanation") or question.get("rubric") else 0.5,
                review_status="needs_review" if detail["correct"] is None else "approved",
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
