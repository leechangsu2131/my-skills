from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.split_subunits_from_plan_table import (  # noqa: E402
    build_groups_from_activity_plan_entry,
    build_groups_from_music_plan_pages,
    normalize_music_unit_title,
)


class FakePage:
    def extract_text(self) -> str:
        return ''


class FakePdf:
    def __init__(self, page_count: int) -> None:
        self.pages = [FakePage() for _ in range(page_count)]


class PlanHoursMetadataTests(unittest.TestCase):
    def test_build_groups_from_activity_plan_entry_keeps_hours_metadata(self) -> None:
        pdf_doc = FakePdf(20)
        parent_group = {
            'title': '1 우리 반 캐릭터 만들기',
            'source_title': '1 우리 반 캐릭터 만들기',
            'start_page': 59,
            'end_page': 70,
            'context': [],
        }
        plan_unit = {
            'activities': [
                {'title': '내가 할 수 있는 표정 만들기', 'hours': 2},
                {'title': '우리 반 캐릭터로 감정 팔찌 만들기', 'hours': 3},
            ]
        }

        with patch('scripts.split_subunits_from_plan_table.find_activity_plan_boundary_page', return_value=None):
            groups = build_groups_from_activity_plan_entry(pdf_doc, parent_group, plan_unit)

        self.assertEqual([group['hours'] for group in groups], [2, 3])

    def test_build_groups_from_music_plan_pages_keeps_hours_metadata(self) -> None:
        pdf_doc = FakePdf(20)
        units = [
            {
                'title': '만나요, 음악 시간',
                'start_page': 2,
                'end_page': 8,
                'rows': [
                    {'title': '마음 열기, 음악 놀이', 'printed_page': 5, 'hours': 2, 'source_page': 3},
                    {'title': '노래 부르기', 'printed_page': 7, 'hours': 1, 'source_page': 3},
                ],
            },
            {
                'title': '느껴요, 음악의 아름다움',
                'start_page': 9,
                'end_page': 15,
                'rows': [
                    {'title': '소리의 느낌', 'printed_page': 12, 'hours': 2, 'source_page': 10},
                    {'title': '음악 듣기', 'printed_page': 14, 'hours': 1, 'source_page': 10},
                ],
            },
        ]

        with patch('scripts.split_subunits_from_plan_table.extract_music_plan_units', return_value=units), patch(
            'scripts.split_subunits_from_plan_table.infer_music_plan_page_offset',
            return_value=0,
        ):
            groups = build_groups_from_music_plan_pages(pdf_doc, 'detail')

        detail_groups = [group for group in groups if group.get('detected_level') == 'detail']
        self.assertEqual([group['hours'] for group in detail_groups[:3]], [1, 2, 1])

    def test_normalize_music_unit_title_adds_missing_first_unit_number(self) -> None:
        self.assertEqual(
            normalize_music_unit_title('만나요, 음악 시간', 1),
            '1 만나요, 음악 시간',
        )
        self.assertEqual(
            normalize_music_unit_title('2 느껴요, 음악의 아름다움', 2),
            '2 느껴요, 음악의 아름다움',
        )
        self.assertEqual(
            normalize_music_unit_title('프로젝트 함께 만드는 공연', 5),
            '프로젝트 함께 만드는 공연',
        )


if __name__ == '__main__':
    unittest.main()
