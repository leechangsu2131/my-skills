#!/usr/bin/env python3
"""Core grading engine."""

from __future__ import annotations

import json
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_config() -> dict:
    with open(PROJECT_ROOT / "config.json", "r", encoding="utf-8") as file_obj:
        return json.load(file_obj)


def normalize_answer(answer: str, config: dict) -> str:
    text = answer.strip() if config.get("strip_whitespace", True) else answer

    if not config.get("case_sensitive", False):
        text = text.lower()

    text = unicodedata.normalize("NFKC", text)

    if config.get("normalize_numbers", True):
        text = re.sub(r"(\d+)\s+([a-zA-Z가-힣])", r"\1\2", text)
        text = re.sub(r"\.0+$", "", text)

    return text


def _fuzzy_ocr_match(norm_student: str, norm_correct: str, grading_config: dict, q_type: str) -> bool:
    if not grading_config.get("fuzzy_ocr_match", False):
        return False
    if q_type == "descriptive":
        return False
    min_len = int(grading_config.get("fuzzy_min_length", 2))
    if len(norm_student) < min_len or len(norm_correct) < min_len:
        return False
    ratio = float(grading_config.get("fuzzy_match_ratio", 0.88))
    return SequenceMatcher(None, norm_student, norm_correct).ratio() >= ratio


def compare_answers(
    student_answer: str,
    correct_answer: str,
    alt_answers: list[str],
    q_type: str,
    config: dict,
) -> Optional[bool]:
    grading_config = config.get("grading", {})

    if q_type == "descriptive" and not grading_config.get("descriptive_auto_grade", False):
        return None

    if not student_answer.strip():
        return False

    norm_student = normalize_answer(student_answer, grading_config)
    norm_correct = normalize_answer(correct_answer, grading_config)

    if norm_student == norm_correct:
        return True

    for alt in alt_answers:
        if norm_student == normalize_answer(alt, grading_config):
            return True

    if _fuzzy_ocr_match(norm_student, norm_correct, grading_config, q_type):
        return True

    for alt in alt_answers:
        if _fuzzy_ocr_match(norm_student, normalize_answer(alt, grading_config), grading_config, q_type):
            return True

    return False


def grade_student(student_answers: dict, answer_key: dict, config: Optional[dict] = None) -> dict:
    if config is None:
        config = load_config()

    student_map = {answer["q_num"]: answer for answer in student_answers.get("answers", [])}

    details = []
    total_score = 0
    correct_count = 0
    wrong_count = 0
    review_count = 0

    for question in answer_key.get("questions", []):
        q_num = question["q_num"]
        correct_answer = question["answer"]
        alt_answers = question.get("alt_answers", [])
        points = question.get("points", 0)
        q_type = question.get("type", "short_answer")

        student_q = student_map.get(q_num, {})
        student_answer = student_q.get("answer", "")

        is_correct = compare_answers(student_answer, correct_answer, alt_answers, q_type, config)

        if is_correct is True:
            points_earned = points
            correct_count += 1
        elif is_correct is False:
            points_earned = 0
            wrong_count += 1
        else:
            points_earned = 0
            review_count += 1

        total_score += points_earned
        details.append(
            {
                "q_num": q_num,
                "correct": is_correct,
                "student_answer": student_answer,
                "correct_answer": correct_answer,
                "points_earned": points_earned,
                "points_possible": points,
                "analysis": None,
            }
        )

    total_points = answer_key.get("total_points", sum(q.get("points", 0) for q in answer_key.get("questions", [])))
    graded_count = correct_count + wrong_count
    accuracy = (correct_count / graded_count * 100) if graded_count > 0 else 0

    return {
        "student_name": student_answers.get("student_name", "Unknown"),
        "student_number": student_answers.get("student_number"),
        "exam_title": answer_key.get("exam_title") or student_answers.get("exam_title"),
        "total_score": total_score,
        "total_points": total_points,
        "correct_count": correct_count,
        "wrong_count": wrong_count,
        "review_count": review_count,
        "accuracy": round(accuracy, 1),
        "details": details,
    }


def grade_batch(extracted_dir: str, answer_key_path: str, output_dir: str) -> list[dict]:
    config = load_config()
    extracted_path = Path(extracted_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    with open(answer_key_path, "r", encoding="utf-8") as file_obj:
        answer_key = json.load(file_obj)

    answer_files = sorted([file for file in extracted_path.glob("*_answers.json") if file.name != "answer_key.json"])

    if not answer_files:
        print(f"⚠️ 추출된 답안 파일이 없습니다: {extracted_dir}")
        return []

    print(f"\n📊 {len(answer_files)}명 채점 시작...\n")

    results = []
    for index, answer_file in enumerate(answer_files, 1):
        with open(answer_file, "r", encoding="utf-8") as file_obj:
            student_answers = json.load(file_obj)

        student_name = student_answers.get("student_name", answer_file.stem)
        print(f"[{index}/{len(answer_files)}] {student_name}")
        result = grade_student(student_answers, answer_key, config)

        out_file = output_path / f"{answer_file.stem.replace('_answers', '_graded')}.json"
        with open(out_file, "w", encoding="utf-8") as file_obj:
            json.dump(result, file_obj, ensure_ascii=False, indent=2)

        review_str = f", 검토 {result['review_count']}" if result["review_count"] else ""
        print(
            f"  ✅ {result['total_score']}/{result['total_points']}점 "
            f"(정답 {result['correct_count']}, 오답 {result['wrong_count']}{review_str})"
        )
        results.append(result)

    avg_score = sum(result["total_score"] for result in results) / len(results) if results else 0
    avg_accuracy = sum(result["accuracy"] for result in results) / len(results) if results else 0
    print(f"\n📋 전체 평균: {avg_score:.1f}점 ({avg_accuracy:.1f}%)")
    return results

