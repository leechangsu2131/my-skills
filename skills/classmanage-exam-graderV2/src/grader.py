from __future__ import annotations

from answer_normalizer import normalize_objective_answer, normalize_short_answer


def grade_submission_item(item: dict, answer: dict) -> dict:
    answer_type = str(answer.get("type", "객관식"))
    if answer_type == "객관식":
        expected = normalize_objective_answer(answer.get("answer", ""))
        actual = normalize_objective_answer(item.get("recognized_answer", ""))
    else:
        expected = normalize_short_answer(answer.get("answer", ""))
        actual = normalize_short_answer(item.get("recognized_answer", ""))

    is_correct = expected == actual
    points_possible = int(answer.get("points", 0))
    return {
        "expected_answer": expected,
        "recognized_answer": actual,
        "is_correct": is_correct,
        "points_possible": points_possible,
        "points_earned": points_possible if is_correct else 0,
    }
