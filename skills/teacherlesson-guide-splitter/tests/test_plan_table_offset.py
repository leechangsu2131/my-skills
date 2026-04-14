from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.split_subunits_from_plan_table import infer_plan_table_page_offset  # noqa: E402


class FakePage:
    def __init__(self, text: str) -> None:
        self._text = text

    def extract_text(self) -> str:
        return self._text


class FakePdf:
    def __init__(self, *pages: str) -> None:
        self.pages = [FakePage(page) for page in pages]


def test_infer_plan_table_page_offset_prefers_full_in_range_mapping() -> None:
    pages = ["" for _ in range(25)]
    pages[15] = "Unit intro"
    pages[18] = "Lesson one"
    pages[22] = "Lesson two"
    pdf_doc = FakePdf(*pages)

    groups = [
        {"title": "Unit intro", "start_page": 21, "end_page": 23},
        {"title": "Lesson one", "start_page": 24, "end_page": 27},
        {"title": "Lesson two", "start_page": 28, "end_page": 30},
    ]

    assert infer_plan_table_page_offset(pdf_doc, groups) == -5
