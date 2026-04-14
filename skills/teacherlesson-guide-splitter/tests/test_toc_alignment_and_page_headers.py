from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.split_subunits_from_plan_table import (  # noqa: E402
    align_toc_entry_starts,
    build_groups_from_page_header_patterns,
)


class FakePage:
    def __init__(self, text: str) -> None:
        self._text = text

    def extract_text(self) -> str:
        return self._text


class FakePdf:
    def __init__(self, *pages: str) -> None:
        self.pages = [FakePage(page) for page in pages]


class TocAlignmentAndPageHeaderTests(unittest.TestCase):
    def test_align_toc_entry_starts_prefers_lead_in_page_before_strong_title_page(self) -> None:
        pdf_doc = FakePdf(
            "목차\n1 즐거운 표현 4\n2 다음 표현 7",
            "활동지",
            "\n".join(
                [
                    "4차시",
                    "핵심 아이디어",
                    "학습 목표",
                    "• 즐거운 표현 만나기",
                ]
            ),
            "단원명 1. 즐거운 표현 차시 1~2/4 교수·학습 자료 과정안\n학습 주제 즐거운 표현 만들기",
            "\n".join(
                [
                    "6차시",
                    "핵심 아이디어",
                    "학습 목표",
                    "• 다음 표현 탐색하기",
                ]
            ),
            "단원명 2. 다음 표현 차시 1~2/6 교수·학습 자료 과정안\n학습 주제 다음 표현 만들기",
        )

        entries = [
            {"title": "1 즐거운 표현", "start_page": 2},
            {"title": "2 다음 표현", "start_page": 5},
        ]

        aligned = align_toc_entry_starts(pdf_doc, entries)

        self.assertEqual([entry["start_page"] for entry in aligned], [3, 5])

    def test_build_groups_from_page_header_patterns_splits_lead_in_and_process_pages(self) -> None:
        pdf_doc = FakePdf(
            "",
            "",
            "",
            "",
            "\n".join(
                [
                    "4차시",
                    "핵심 아이디어",
                    "학습 목표",
                    "• 다양한 재료 만나기",
                    "• 표현 방법 알아보기",
                ]
            ),
            "단원명 1. 즐거운 표현 차시 1~2/4 교수·학습 자료 과정안\n학습 주제 즐거운 표현 만들기",
        )

        parent_group = {
            "title": "1 즐거운 표현",
            "source_title": "1 즐거운 표현",
            "start_page": 5,
            "end_page": 6,
            "context": [],
        }

        groups = build_groups_from_page_header_patterns(pdf_doc, parent_group)

        self.assertEqual(
            [(group["title"], group["start_page"], group["end_page"]) for group in groups],
            [
                ("다양한 재료 만나기 / 표현 방법 알아보기", 5, 5),
                ("즐거운 표현 만들기", 6, 6),
            ],
        )


if __name__ == "__main__":
    unittest.main()
