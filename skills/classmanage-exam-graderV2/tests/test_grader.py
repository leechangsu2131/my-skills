import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))

from grader import grade_submission_item  # type: ignore


def test_grade_submission_item_scores_objective_match():
    item = {"question_number": 1, "recognized_answer": "②"}
    answer = {"number": 1, "answer": "②", "points": 5, "type": "객관식"}

    result = grade_submission_item(item, answer)

    assert result["is_correct"] is True
    assert result["points_earned"] == 5


def test_grade_submission_item_flags_short_answer_mismatch():
    item = {"question_number": 2, "recognized_answer": "x=3"}
    answer = {"number": 2, "answer": "x=4", "points": 4, "type": "단답형"}

    result = grade_submission_item(item, answer)

    assert result["is_correct"] is False
    assert result["points_earned"] == 0
