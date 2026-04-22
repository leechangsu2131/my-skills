from packages.contracts.models import AnswerKey
from packages.contracts.models import ReviewedSubmission
from packages.contracts.models import ReviewItem
from webapp import schemas as webapp_schemas


def test_answer_key_resolves_total_points_from_questions() -> None:
    payload = AnswerKey(
        exam_title="Unit Quiz",
        questions=[
            {"q_num": 1, "answer": "A", "points": 5},
            {"q_num": 2, "answer": "B", "points": 10},
        ],
    )

    assert payload.resolved_total_points == 15


def test_webapp_schema_module_reexports_contract_models() -> None:
    item = ReviewItem(
        q_num=1,
        correct=True,
        student_answer="A",
        correct_answer="A",
        points_earned=5,
        points_possible=5,
        feedback_text="ok",
        feedback_source="system",
        feedback_confidence=0.9,
        review_status="approved",
    )

    payload = webapp_schemas.ReviewedSubmission(
        student_name="Kim",
        total_score=5,
        total_points=5,
        correct_count=1,
        wrong_count=0,
        review_count=0,
        items=[item],
    )

    assert webapp_schemas.ReviewedSubmission is ReviewedSubmission
    assert isinstance(payload, ReviewedSubmission)
