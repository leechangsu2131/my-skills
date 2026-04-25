from __future__ import annotations

import json
import re
from pathlib import Path

import fitz
from packages.answer_key_extraction.service import load_answer_key_json
from packages.answer_key_extraction.service import parse_answer_key_pdf
from packages.annotation.service import annotate_pdf
from packages.contracts.models import ReviewedSubmission
from packages.contracts.models import ReviewItem
from packages.grading.service import grade_student
from packages.grading.service import load_config
from packages.grading.service import merge_analysis
from packages.student_extraction.service import extract_answers
from packages.student_extraction.service import extract_answer_groups


def parse_answer_key_file(path: Path) -> dict:
    if path.suffix.lower() == ".json":
        return load_answer_key_json(str(path))
    return parse_answer_key_pdf(str(path))


def parse_student_file(
    path: Path,
    *,
    answer_key: dict | None = None,
    blank_exam_path: Path | None = None,
    metadata_dir: Path | None = None,
    student_page_offset: int | None = None,
    auto_pick_student_pages: bool | None = None,
) -> dict:
    if path.suffix.lower() == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    if blank_exam_path is None:
        raise ValueError("blank_exam_path is required for PDF student parsing")
    return extract_answers(
        str(path),
        blank_exam_path=str(blank_exam_path),
        answer_key=answer_key,
        metadata_dir=metadata_dir,
        student_page_offset=student_page_offset,
        auto_pick_student_pages=auto_pick_student_pages,
    )


def parse_student_file_bundle(
    path: Path,
    *,
    answer_key: dict | None = None,
    blank_exam_path: Path | None = None,
    metadata_dir: Path | None = None,
    student_page_offset: int | None = None,
    auto_pick_student_pages: bool | None = None,
) -> list[dict]:
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return _normalize_student_bundle(payload, path.stem)
        return _normalize_student_bundle([payload], path.stem)
    if blank_exam_path is None:
        raise ValueError("blank_exam_path is required for PDF student parsing")
    effective_metadata_dir = metadata_dir / path.stem if metadata_dir else None
    return _normalize_student_bundle(
        extract_answer_groups(
            str(path),
            blank_exam_path=str(blank_exam_path),
            answer_key=answer_key,
            metadata_dir=effective_metadata_dir,
            student_page_offset=student_page_offset,
            auto_pick_student_pages=auto_pick_student_pages,
        ),
        path.stem,
    )


def materialize_submission_source_pdf(
    source_path: Path,
    student_answers: dict,
    output_dir: Path,
) -> Path:
    if source_path.suffix.lower() != ".pdf":
        return source_path

    ocr_meta = dict(student_answers.get("ocr_meta") or {})
    try:
        page_offset = int(ocr_meta.get("student_page_offset", 0))
        template_page_count = int(ocr_meta.get("template_page_count", 0))
        student_pdf_page_count = int(ocr_meta.get("student_pdf_page_count", 0))
        group_index = int(ocr_meta.get("group_index", 1))
        group_count = int(ocr_meta.get("group_count", 1))
    except (TypeError, ValueError):
        return source_path

    if template_page_count <= 0:
        return source_path
    if page_offset == 0 and template_page_count >= max(student_pdf_page_count, template_page_count) and group_count == 1:
        return source_path

    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = f"_group{group_index:02d}" if group_count > 1 else "_selected"
    sliced_path = output_dir / f"{_slugify_filename(source_path.stem)}{suffix}.pdf"

    source_doc = fitz.open(source_path)
    target_doc = fitz.open()
    try:
        last_page = min(page_offset + template_page_count - 1, source_doc.page_count - 1)
        if page_offset < 0 or page_offset >= source_doc.page_count:
            return source_path
        target_doc.insert_pdf(source_doc, from_page=page_offset, to_page=last_page)
        target_doc.save(sliced_path)
    finally:
        target_doc.close()
        source_doc.close()
    return sliced_path


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
                confidence_score=float(student_entry["confidence_score"])
                if student_entry.get("confidence_score") is not None
                else None,
                alignment_score=float(student_entry["alignment_score"])
                if student_entry.get("alignment_score") is not None
                else None,
                extraction_method=student_entry.get("extraction_method"),
                review_reason=list(student_entry.get("review_reason") or []),
                page=student_entry.get("page"),
                bbox=list(student_entry.get("bbox")) if student_entry.get("bbox") is not None else None,
                review_bbox=list(student_entry.get("review_bbox")) if student_entry.get("review_bbox") is not None else None,
                template_bbox=list(student_entry.get("template_bbox")) if student_entry.get("template_bbox") is not None else None,
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


def _normalize_student_bundle(students: list[dict], fallback_name: str) -> list[dict]:
    normalized: list[dict] = []
    seen_names: dict[str, int] = {}
    multiple = len(students) > 1
    for index, student in enumerate(students, start=1):
        payload = dict(student)
        base_name = str(payload.get("student_name") or fallback_name).strip() or fallback_name
        duplicate_count = seen_names.get(base_name, 0) + 1
        seen_names[base_name] = duplicate_count
        if multiple and (base_name == fallback_name or duplicate_count > 1):
            payload["student_name"] = f"{base_name} #{index}"
        else:
            payload["student_name"] = base_name
        normalized.append(payload)
    return normalized


def _slugify_filename(value: str) -> str:
    normalized = re.sub(r"[^\w\-]+", "_", value.strip(), flags=re.UNICODE)
    return normalized.strip("_") or "student"


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
