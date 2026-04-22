"""Public grading service surface."""

from packages.grading.analysis_merger import merge_analysis
from packages.grading.analysis_merger import merge_batch
from packages.grading.grader import compare_answers
from packages.grading.grader import grade_batch
from packages.grading.grader import grade_student
from packages.grading.grader import load_config
from packages.grading.grader import normalize_answer
from packages.grading.subjective import grade_subjective_batch

__all__ = [
    "compare_answers",
    "grade_batch",
    "grade_student",
    "grade_subjective_batch",
    "load_config",
    "merge_analysis",
    "merge_batch",
    "normalize_answer",
]
