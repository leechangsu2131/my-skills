"""Backward-compatible wrapper for the student extraction package."""

from packages.student_extraction.service import extract_answers
from packages.student_extraction.service import extract_batch
from packages.student_extraction.service import extract_json_from_response
from packages.student_extraction.service import load_config
from packages.student_extraction.service import load_prompt
from packages.student_extraction.service import main
from packages.student_extraction.service import run_gemini_ocr

__all__ = [
    "extract_answers",
    "extract_batch",
    "extract_json_from_response",
    "load_config",
    "load_prompt",
    "main",
    "run_gemini_ocr",
]


if __name__ == "__main__":
    main()
