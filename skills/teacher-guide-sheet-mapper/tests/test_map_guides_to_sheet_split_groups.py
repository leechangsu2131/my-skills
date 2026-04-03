import json
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch

import map_guides_to_sheet


class MapGuidesToSheetSplitGroupTests(unittest.TestCase):
    def test_build_rows_from_split_groups_reads_groups_json(self):
        groups_payload = {
            "pdf": "math_guide_3_1.pdf",
            "groups": [
                {
                    "index": 1,
                    "title": "단원 도입",
                    "start_page": 57,
                    "end_page": 59,
                    "context": [],
                    "detected_level": "detail",
                    "parent_unit_title": "1단원",
                },
                {
                    "index": 2,
                    "title": "덧셈",
                    "start_page": 60,
                    "end_page": 63,
                    "context": [],
                    "detected_level": "detail",
                    "parent_unit_title": "1단원",
                },
                {
                    "index": 3,
                    "title": "단원 도입",
                    "start_page": 107,
                    "end_page": 109,
                    "context": [],
                    "detected_level": "detail",
                    "parent_unit_title": "2단원",
                },
                {
                    "index": 4,
                    "title": "선의 종류",
                    "start_page": 110,
                    "end_page": 115,
                    "context": [],
                    "detected_level": "detail",
                    "parent_unit_title": "2단원",
                },
            ],
        }

        fake_run = {
            "groups_path": Path("math_guide_3_1/groups.json"),
            "pdf_dir": Path("math_guide_3_1/pdf_splits"),
            "source_name": groups_payload["pdf"],
            "groups": groups_payload["groups"],
        }

        with patch.object(map_guides_to_sheet, "collect_split_group_runs", return_value=[fake_run]), patch.object(
            map_guides_to_sheet,
            "find_split_pdf_for_group",
            side_effect=[
                r"C:\fake\[math]_subunit_01_intro_p57-59.pdf",
                r"C:\fake\[math]_subunit_02_addition_p60-63.pdf",
                r"C:\fake\[math]_subunit_03_intro_p107-109.pdf",
                r"C:\fake\[math]_subunit_04_lines_p110-115.pdf",
            ],
        ):
            rows = map_guides_to_sheet.build_rows_from_split_groups("수학", "수학", grade_str="3-1")

        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0]["대단원"], "1단원")
        self.assertEqual(rows[0]["차시"], "1")
        self.assertEqual(rows[0]["시작페이지"], 57)
        self.assertTrue(rows[0]["pdf파일"].endswith("subunit_01_intro_p57-59.pdf"))
        self.assertEqual(rows[1]["대단원"], "1단원")
        self.assertEqual(rows[1]["차시"], "2")
        self.assertEqual(rows[2]["대단원"], "2단원")
        self.assertEqual(rows[2]["차시"], "1")
        self.assertEqual(rows[3]["대단원"], "2단원")
        self.assertEqual(rows[3]["차시"], "2")

    def test_build_rows_from_split_groups_infers_math_unit_titles(self):
        fake_run = {
            "groups_path": Path("math_guide_3_1/groups.json"),
            "pdf_dir": Path("math_guide_3_1/pdf_splits"),
            "source_name": "math_guide_3_1.pdf",
            "groups": [
                {"index": 1, "title": "단원 도입", "start_page": 16, "end_page": 18, "context": [], "detected_level": "detail"},
                {"index": 2, "title": "덧셈을 해 볼까요", "start_page": 19, "end_page": 22, "context": [], "detected_level": "detail"},
                {"index": 3, "title": "뺄셈을 해 볼까요", "start_page": 23, "end_page": 26, "context": [], "detected_level": "detail"},
                {"index": 4, "title": "단원 도입", "start_page": 66, "end_page": 68, "context": [], "detected_level": "detail"},
                {"index": 5, "title": "각을 알아볼까요", "start_page": 75, "end_page": 78, "context": [], "detected_level": "detail"},
            ],
        }

        with patch.object(map_guides_to_sheet, "collect_split_group_runs", return_value=[fake_run]), patch.object(
            map_guides_to_sheet,
            "find_split_pdf_for_group",
            side_effect=[
                r"C:\fake\math_01.pdf",
                r"C:\fake\math_02.pdf",
                r"C:\fake\math_03.pdf",
                r"C:\fake\math_04.pdf",
                r"C:\fake\math_05.pdf",
            ],
        ):
            rows = map_guides_to_sheet.build_rows_from_split_groups("수학", "수학", grade_str="3-1")

        self.assertEqual(rows[0]["대단원"], "1단원 덧셈과 뺄셈")
        self.assertEqual(rows[3]["대단원"], "2단원 평면도형")

    def test_build_rows_from_split_groups_uses_group_hours_for_lesson_ranges(self):
        fake_run = {
            "groups_path": Path("art_guide_3/groups.json"),
            "pdf_dir": Path("art_guide_3/pdf_splits"),
            "source_name": "art_guide_3.pdf",
            "groups": [
                {
                    "index": 1,
                    "title": "우리 반 캐릭터 만들기",
                    "start_page": 59,
                    "end_page": 63,
                    "context": [],
                    "detected_level": "detail",
                    "parent_unit_title": "1 함께 만드는 캐릭터",
                    "hours": 2,
                },
                {
                    "index": 2,
                    "title": "우리 반 캐릭터로 감정 팔찌 만들기",
                    "start_page": 64,
                    "end_page": 70,
                    "context": [],
                    "detected_level": "detail",
                    "parent_unit_title": "1 함께 만드는 캐릭터",
                    "hours": 3,
                },
                {
                    "index": 3,
                    "title": "보호색 찾아 새알 숨기기",
                    "start_page": 71,
                    "end_page": 75,
                    "context": [],
                    "detected_level": "detail",
                    "parent_unit_title": "2 조형 요소 색, 선, 형",
                    "hours": 1,
                },
            ],
        }

        with patch.object(map_guides_to_sheet, "collect_split_group_runs", return_value=[fake_run]), patch.object(
            map_guides_to_sheet,
            "find_split_pdf_for_group",
            side_effect=[
                r"C:\fake\art_01.pdf",
                r"C:\fake\art_02.pdf",
                r"C:\fake\art_03.pdf",
            ],
        ):
            rows = map_guides_to_sheet.build_rows_from_split_groups("미술", "미술", grade_str="3")

        self.assertEqual([row["차시"] for row in rows], ["1~2", "3~5", "1"])

    def test_expand_rows_by_lesson_range_splits_plain_ranges_into_separate_rows(self):
        rows = [
            {"과목": "사회", "대단원": "1단원", "차시": "13~14", "수업내용": "우리 고장의 행사"},
            {"과목": "사회", "대단원": "1단원", "차시": "15", "수업내용": "정리"},
            {"과목": "국어", "대단원": "1단원", "차시": "2(2~3)", "수업내용": "감각적 표현"},
        ]

        expanded = map_guides_to_sheet.expand_rows_by_lesson_range(rows)

        self.assertEqual([row["차시"] for row in expanded], ["13", "14", "15", "2(2~3)"])

    def test_generate_general_data_expands_split_range_rows_before_return(self):
        split_rows = [
            {
                "과목": "미술",
                "대단원": "1 함께 만드는 캐릭터",
                "차시": "1~2",
                "수업내용": "우리 반 캐릭터 만들기",
                "pdf파일": r"C:\fake\art_01.pdf",
            },
            {
                "과목": "미술",
                "대단원": "1 함께 만드는 캐릭터",
                "차시": "3~4",
                "수업내용": "우리 반 캐릭터로 감정 팔찌 만들기",
                "pdf파일": r"C:\fake\art_02.pdf",
            },
        ]

        with patch.object(map_guides_to_sheet, "build_rows_from_split_groups", return_value=split_rows), patch.object(
            map_guides_to_sheet,
            "build_rows_from_annual_plan",
            return_value=[],
        ):
            rows = map_guides_to_sheet.generate_general_data("미술", "미술", max_unit=8, grade_str="3")

        self.assertEqual([row["차시"] for row in rows], ["1", "2", "3", "4"])
        self.assertEqual([row["수업내용"] for row in rows], ["우리 반 캐릭터 만들기", "우리 반 캐릭터 만들기", "우리 반 캐릭터로 감정 팔찌 만들기", "우리 반 캐릭터로 감정 팔찌 만들기"])

    def test_build_rows_from_annual_plan_resets_lesson_range_per_unit(self):
        entries = [
            {
                "unit_num": 1,
                "unit_title": "1. 우리가 사는 곳",
                "subunit": "1. 우리 주변",
                "lesson_range": "1",
                "title": "단원 도입",
            },
            {
                "unit_num": 1,
                "unit_title": "1. 우리가 사는 곳",
                "subunit": "1. 우리 주변",
                "lesson_range": "4~5",
                "title": "우리 주변 살펴보기",
            },
            {
                "unit_num": 2,
                "unit_title": "2. 일상에서 만나는 과거",
                "subunit": "1. 옛날과 오늘",
                "lesson_range": "19",
                "title": "단원 도입",
            },
            {
                "unit_num": 2,
                "unit_title": "2. 일상에서 만나는 과거",
                "subunit": "1. 옛날과 오늘",
                "lesson_range": "20~21",
                "title": "옛날과 오늘 비교하기",
            },
        ]

        with patch.object(map_guides_to_sheet, "find_annual_plan_pdf", return_value=r"C:\fake\social_plan.pdf"), patch.object(
            map_guides_to_sheet,
            "extract_annual_plan_entries",
            return_value=entries,
        ), patch.object(
            map_guides_to_sheet,
            "find_best_pdf",
            return_value=r"C:\fake\lesson.pdf",
        ):
            rows = map_guides_to_sheet.build_rows_from_annual_plan("사회", "사회", grade_str="3-1")

        self.assertEqual([row["차시"] for row in rows], ["1", "4~5", "1", "2~3"])

    def test_build_rows_from_split_groups_uses_context_grade_and_skips_plan_groups(self):
        workspace_dir = Path(__file__).resolve().parents[1]
        tmp_dir = workspace_dir / "_test_split_group_runs"
        shutil.rmtree(tmp_dir, ignore_errors=True)
        tmp_dir.mkdir(parents=True, exist_ok=True)
        try:
            run_dir = tmp_dir / "미술"
            pdf_dir = run_dir / "pdf_splits"
            pdf_dir.mkdir(parents=True, exist_ok=True)

            groups_payload = {
                "pdf": "미술.pdf",
                "split_level": "detail",
                "groups": [
                    {
                        "index": 1,
                        "title": "미술 시간 계획표",
                        "start_page": 55,
                        "end_page": 58,
                        "context": ["3학년"],
                        "detected_level": "plan",
                    },
                    {
                        "index": 2,
                        "title": "다양한 캐릭터 만나기",
                        "start_page": 59,
                        "end_page": 69,
                        "context": ["3학년"],
                        "detected_level": "detail",
                        "parent_unit_title": "1단원",
                    },
                    {
                        "index": 3,
                        "title": "학급 캐릭터 만들기",
                        "start_page": 70,
                        "end_page": 70,
                        "context": ["3학년"],
                        "detected_level": "detail",
                        "parent_unit_title": "1단원",
                    },
                    {
                        "index": 4,
                        "title": "선으로 동물 표현하기",
                        "start_page": 82,
                        "end_page": 82,
                        "context": ["3학년"],
                        "detected_level": "detail",
                        "parent_unit_title": "2단원",
                    },
                ],
            }
            (run_dir / "groups.json").write_text(
                json.dumps(groups_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            for filename in (
                "art_subunit_02_intro_p59-69.pdf",
                "art_subunit_03_make_p70-70.pdf",
                "art_subunit_04_line_p82-82.pdf",
            ):
                (pdf_dir / filename).write_bytes(b"")

            with patch.object(map_guides_to_sheet, "GUIDE_SEARCH_DIRS", [tmp_dir]):
                rows = map_guides_to_sheet.build_rows_from_split_groups(
                    "미술",
                    "미술",
                    grade_str="3",
                )
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

        self.assertEqual(len(rows), 3)
        self.assertEqual([row["대단원"] for row in rows], ["1단원", "1단원", "2단원"])
        self.assertEqual([row["차시"] for row in rows], ["1", "2", "1"])
        self.assertTrue(rows[0]["pdf파일"].endswith("art_subunit_02_intro_p59-69.pdf"))
        self.assertEqual(rows[0]["시작페이지"], 59)
        self.assertEqual(rows[2]["시작페이지"], 82)

    def test_generate_general_data_merges_annual_rows_with_split_pdfs_when_aligned(self):
        split_rows = [
            {
                "과목": "사회",
                "대단원": "1단원",
                "차시": "1",
                "수업내용": "단원 도입",
                "pdf파일": r"C:\fake\split_01.pdf",
                "시작페이지": 1,
                "끝페이지": 8,
                "비고": "사회1",
            },
            {
                "과목": "사회",
                "대단원": "1단원",
                "차시": "2",
                "수업내용": "장소에 대해 알아볼까요",
                "pdf파일": r"C:\fake\split_02.pdf",
                "시작페이지": 9,
                "끝페이지": 15,
                "비고": "사회1",
            },
        ]
        annual_rows = [
            {
                "과목": "사회",
                "대단원": "1. 우리가 사는 곳",
                "차시": "1",
                "수업내용": "단원 도입",
                "pdf파일": r"C:\fake\wrong_01.pdf",
            },
            {
                "과목": "사회",
                "대단원": "1. 우리가 사는 곳",
                "차시": "2",
                "수업내용": "장소에 대해 알아볼까요",
                "pdf파일": r"C:\fake\wrong_02.pdf",
            },
        ]

        with patch.object(map_guides_to_sheet, "build_rows_from_split_groups", return_value=split_rows), patch.object(
            map_guides_to_sheet,
            "build_rows_from_annual_plan",
            return_value=annual_rows,
        ):
            rows = map_guides_to_sheet.generate_general_data("사회", "사회", max_unit=4, grade_str="3-1")

        self.assertEqual([row["대단원"] for row in rows], ["1. 우리가 사는 곳", "1. 우리가 사는 곳"])
        self.assertEqual([row["pdf파일"] for row in rows], [r"C:\fake\split_01.pdf", r"C:\fake\split_02.pdf"])
        self.assertEqual([row["시작페이지"] for row in rows], [1, 9])

    def test_generate_general_data_prefers_split_rows_when_more_detailed(self):
        split_rows = [{"과목": "수학", "차시": str(i)} for i in range(1, 47)]
        annual_rows = [{"과목": "수학", "차시": str(i)} for i in range(1, 19)]

        with patch.object(map_guides_to_sheet, "build_rows_from_split_groups", return_value=split_rows), patch.object(
            map_guides_to_sheet,
            "build_rows_from_annual_plan",
            return_value=annual_rows,
        ):
            rows = map_guides_to_sheet.generate_general_data("수학", "수학", max_unit=6, grade_str="3-1")

        self.assertEqual(rows, split_rows)


if __name__ == "__main__":
    unittest.main()
