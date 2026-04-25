from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, computed_field


QuestionType = Literal["multiple_choice", "short_answer", "descriptive", "unknown"]
ConfidenceLevel = Literal["high", "medium", "low"]


class AnswerKeyQuestion(BaseModel):
    q_num: int
    type: QuestionType = "short_answer"
    answer: str
    alt_answers: list[str] = Field(default_factory=list)
    points: float
    rubric: str | None = None
    explanation: str | None = None
    question_text: str | None = None


class AnswerKey(BaseModel):
    exam_title: str | None = None
    total_points: float | None = None
    questions: list[AnswerKeyQuestion]

    @computed_field
    @property
    def resolved_total_points(self) -> float:
        if self.total_points is not None:
            return self.total_points
        return sum(question.points for question in self.questions)


class StudentAnswerEntry(BaseModel):
    q_num: int
    type: QuestionType = "unknown"
    answer: str = ""
    confidence: ConfidenceLevel = "medium"
    confidence_score: float | None = None
    alignment_score: float | None = None
    extraction_method: str | None = None
    review_reason: list[str] = Field(default_factory=list)
    page: int | None = None
    bbox: list[float] | None = None
    review_bbox: list[float] | None = None
    template_bbox: list[float] | None = None
    requires_review: bool = False


class StudentAnswer(BaseModel):
    student_name: str
    student_number: int | None = None
    exam_title: str | None = None
    answers: list[StudentAnswerEntry]


class ReviewItem(BaseModel):
    q_num: int
    correct: bool | None
    student_answer: str
    correct_answer: str
    points_earned: float
    points_possible: float
    feedback_text: str
    feedback_source: str
    feedback_confidence: float
    review_status: Literal["approved", "needs_review"]
    confidence_score: float | None = None
    alignment_score: float | None = None
    extraction_method: str | None = None
    review_reason: list[str] = Field(default_factory=list)
    page: int | None = None
    bbox: list[float] | None = None
    review_bbox: list[float] | None = None
    template_bbox: list[float] | None = None
    student_crop_url: str | None = None
    reference_crop_url: str | None = None
    student_page_url: str | None = None
    reference_page_url: str | None = None
    manual_page_review: bool = False
    question_text: str | None = None
    rubric: str | None = None


class ReviewedSubmission(BaseModel):
    student_name: str
    student_number: int | None = None
    exam_title: str | None = None
    total_score: float
    total_points: float
    correct_count: int
    wrong_count: int
    review_count: int
    items: list[ReviewItem]
