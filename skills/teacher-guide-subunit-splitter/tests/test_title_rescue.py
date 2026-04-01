from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.split_subunits_from_plan_table import (  # noqa: E402
    build_groups_from_tables,
    infer_plan_table_page_offset,
    resolve_display_title_from_page_heading,
    title_has_stable_lesson_signal,
    title_needs_page_heading_rescue,
)


class FakePage:
    def __init__(self, text: str) -> None:
        self._text = text

    def extract_text(self) -> str:
        return self._text


class FakePdf:
    def __init__(self, *pages: str) -> None:
        self.pages = [FakePage(page) for page in pages]


def test_title_rescue_detects_generic_noise_not_just_math_words() -> None:
    assert title_needs_page_heading_rescue("05. 수학과 교과용 도서의 유기적인 활용 및")
    assert title_needs_page_heading_rescue("우리 지역의 문화유산 보전 및")
    assert title_has_stable_lesson_signal("(몇십)_(몇)을 알아볼까요")
    assert not title_needs_page_heading_rescue("(몇십)_(몇)을 알아볼까요")
    assert not title_needs_page_heading_rescue("직각을 알아볼까요")


def test_resolve_display_title_prefers_start_page_heading_for_truncated_titles() -> None:
    pdf_doc = FakePdf(
        "\n".join(
            [
                "사회과 교과용 도서의 활용",
                "단원 개관",
                "우리 지역의 문화유산 보전과 활용",
                "교수 · 학습 과정안",
            ]
        )
    )

    resolved = resolve_display_title_from_page_heading(
        pdf_doc,
        1,
        "우리 지역의 문화유산 보전 및",
        parent_title="사회과 교과용 도서의 활용",
    )

    assert resolved == "우리 지역의 문화유산 보전과 활용"


def test_resolve_display_title_keeps_existing_title_when_it_is_already_stable() -> None:
    pdf_doc = FakePdf(
        "\n".join(
            [
                "2. 평면도형",
                "단원 개관",
                "직각을 알아볼까요",
            ]
        )
    )

    resolved = resolve_display_title_from_page_heading(
        pdf_doc,
        1,
        "직각을 알아볼까요",
        parent_title="2. 평면도형",
    )

    assert resolved == "직각을 알아볼까요"


def test_build_groups_from_tables_keeps_repeated_titles_as_separate_occurrences() -> None:
    tables = [
        [
            ["단원 도입", "", "", "57-59"],
            ["덧셈을 해 볼까요⑴", "", "", "60-63"],
            ["하하! 놀이와 만나요", "", "", "86-87"],
            ["됐다! 마무리", "", "", "90-91"],
        ],
        [
            ["단원 도입", "", "", "107-109"],
            ["선의 종류에는 어떤 것이 있을까요", "", "", "110-115"],
            ["하하! 놀이와 만나요", "", "", "136-137"],
            ["됐다! 마무리", "", "", "142-143"],
        ],
    ]

    groups = build_groups_from_tables(tables, guide_column_override=3)

    assert [(group["title"], group["start_page"], group["end_page"]) for group in groups] == [
        ("단원 도입", 57, 59),
        ("덧셈을 해 볼까요⑴", 60, 63),
        ("하하! 놀이와 만나요", 86, 87),
        ("됐다! 마무리", 90, 91),
        ("단원 도입", 107, 109),
        ("선의 종류에는 어떤 것이 있을까요", 110, 115),
        ("하하! 놀이와 만나요", 136, 137),
        ("됐다! 마무리", 142, 143),
    ]
