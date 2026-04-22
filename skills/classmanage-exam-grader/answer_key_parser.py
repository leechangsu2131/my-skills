"""Backward-compatible wrapper for the answer-key extraction package."""

from packages.answer_key_extraction.service import create_answer_key_interactive
from packages.answer_key_extraction.service import load_answer_key_json
from packages.answer_key_extraction.service import main
from packages.answer_key_extraction.service import parse_answer_key_pdf
from packages.answer_key_extraction.service import save_answer_key

__all__ = [
    "create_answer_key_interactive",
    "load_answer_key_json",
    "main",
    "parse_answer_key_pdf",
    "save_answer_key",
]


if __name__ == "__main__":
    main()
