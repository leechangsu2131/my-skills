import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import map_guides_to_sheet


class MapGuidesToSheetSplitGroupTests(unittest.TestCase):
    def test_build_rows_from_split_groups_reads_groups_json(self):
        groups_payload = {
            "pdf": "怨듯넻?먮즺_?섑븰 吏?꾩꽌 3-1_媛곷줎.PDF",
            "groups": [
                {
                    "index": 1,
                    "title": "?⑥썝 ?꾩엯",
                    "start_page": 57,
                    "end_page": 59,
                    "context": [],
                    "detected_level": "detail",
                },
                {
                    "index": 2,
                    "title": "?㏃뀍????蹂쇨퉴?붴뫒",
                    "start_page": 60,
                    "end_page": 63,
                    "context": [],
                    "detected_level": "detail",
                },
                {
                    "index": 3,
                    "title": "?⑥썝 ?꾩엯",
                    "start_page": 107,
                    "end_page": 109,
                    "context": [],
                    "detected_level": "detail",
                },
                {
                    "index": 4,
                    "title": "?좎쓽 醫낅쪟?먮뒗 ?대뼡 寃껋씠 ?덉쓣源뚯슂",
                    "start_page": 110,
                    "end_page": 115,
                    "context": [],
                    "detected_level": "detail",
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
            rows = map_guides_to_sheet.build_rows_from_split_groups("?섑븰", "?섑븰", grade_str="3-1")

        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0]["??⑥썝"], "1?⑥썝")
        self.assertEqual(rows[0]["李⑥떆"], "1")
        self.assertEqual(rows[0]["?쒖옉?섏씠吏"], 57)
        self.assertTrue(rows[0]["pdf?뚯씪"].endswith("subunit_01_intro_p57-59.pdf"))
        self.assertEqual(rows[1]["??⑥썝"], "1?⑥썝")
        self.assertEqual(rows[1]["李⑥떆"], "2")
        self.assertEqual(rows[2]["??⑥썝"], "2?⑥썝")
        self.assertEqual(rows[2]["李⑥떆"], "1")
        self.assertEqual(rows[3]["??⑥썝"], "2?⑥썝")
        self.assertEqual(rows[3]["李⑥떆"], "2")

    def test_build_rows_from_annual_plan_resets_lesson_range_per_unit(self):
        entries = [
            {
                "unit_num": 1,
                "unit_title": "1. ?곕━媛 ?щ뒗 怨?,",
                "subunit": "1. ?곕━媛 ?щ뒗 怨녹쓽 ?щ윭 ?μ냼",
                "lesson_range": "1",
                "title": "?⑥썝 ?꾩엯",
            },
            {
                "unit_num": 1,
                "unit_title": "1. ?곕━媛 ?щ뒗 怨?,",
                "subunit": "1. ?곕━媛 ?щ뒗 怨녹쓽 ?щ윭 ?μ냼",
                "lesson_range": "4~5",
                "title": "?곕━媛 ?щ뒗 怨녹뿉 ????뚯븘蹂쇨퉴??,",
            },
            {
                "unit_num": 2,
                "unit_title": "2. ?쇱긽?먯꽌 留뚮굹??怨쇨굅",
                "subunit": "1. ?쏅궇怨??ㅻ뒛?좎쓽 紐⑥뒿",
                "lesson_range": "19",
                "title": "?⑥썝 ?꾩엯",
            },
            {
                "unit_num": 2,
                "unit_title": "2. ?쇱긽?먯꽌 留뚮굹??怨쇨굅",
                "subunit": "1. ?쏅궇怨??ㅻ뒛?좎쓽 紐⑥뒿",
                "lesson_range": "20~21",
                "title": "?쏅궇怨??ㅻ뒛?좎쓣 鍮꾧탳??蹂쇨퉴??,",
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
            rows = map_guides_to_sheet.build_rows_from_annual_plan("?ы쉶", "?ы쉶", grade_str="3-1")

        self.assertEqual([row["李⑥떆"] for row in rows], ["1", "4~5", "1", "2~3"])

    def test_build_rows_from_split_groups_uses_context_grade_and_skips_plan_groups(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            run_dir = Path(tmp_dir) / "\ubbf8\uc220"
            pdf_dir = run_dir / "pdf_splits"
            pdf_dir.mkdir(parents=True)

            groups_payload = {
                "pdf": "\ubbf8\uc220.pdf",
                "split_level": "detail",
                "groups": [
                    {
                        "index": 1,
                        "title": "\ubbf8\uc220 \uc2dc\uac04 \uacc4\ud68d\ud45c",
                        "start_page": 55,
                        "end_page": 58,
                        "context": ["3\ud559\ub144"],
                        "detected_level": "plan",
                    },
                    {
                        "index": 2,
                        "title": "\ub2e4\uc591\ud55c \uce90\ub9ad\ud130 \ub9cc\ub098\uae30",
                        "start_page": 59,
                        "end_page": 69,
                        "context": ["3\ud559\ub144"],
                        "detected_level": "detail",
                        "parent_unit_title": "1\ub2e8\uc6d0",
                    },
                    {
                        "index": 3,
                        "title": "\ud559\uae09 \uce90\ub9ad\ud130 \ub9cc\ub4e4\uae30",
                        "start_page": 70,
                        "end_page": 70,
                        "context": ["3\ud559\ub144"],
                        "detected_level": "detail",
                        "parent_unit_title": "1\ub2e8\uc6d0",
                    },
                    {
                        "index": 4,
                        "title": "\uc120\uc73c\ub85c \ub3d9\ubb3c \ud45c\ud604\ud558\uae30",
                        "start_page": 82,
                        "end_page": 82,
                        "context": ["3\ud559\ub144"],
                        "detected_level": "detail",
                        "parent_unit_title": "2\ub2e8\uc6d0",
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

            with patch.object(map_guides_to_sheet, "GUIDE_SEARCH_DIRS", [Path(tmp_dir)]):
                rows = map_guides_to_sheet.build_rows_from_split_groups(
                    "\ubbf8\uc220",
                    "\ubbf8\uc220",
                    grade_str="3",
                )

        self.assertEqual(len(rows), 3)
        self.assertEqual(
            [row["??⑥썝"] for row in rows],
            ["1\ub2e8\uc6d0", "1\ub2e8\uc6d0", "2\ub2e8\uc6d0"],
        )
        self.assertEqual([row["李⑥떆"] for row in rows], ["1", "2", "1"])
        self.assertTrue(rows[0]["pdf?뚯씪"].endswith("art_subunit_02_intro_p59-69.pdf"))
        self.assertEqual(rows[0]["?쒖옉?섏씠吏"], 59)
        self.assertEqual(rows[2]["?쒖옉?섏씠吏"], 82)

    def test_generate_general_data_prefers_split_rows_when_more_detailed(self):
        split_rows = [{"怨쇰ぉ": "?섑븰", "李⑥떆": str(i)} for i in range(1, 47)]
        annual_rows = [{"怨쇰ぉ": "?섑븰", "李⑥떆": str(i)} for i in range(1, 19)]

        with patch.object(map_guides_to_sheet, "build_rows_from_split_groups", return_value=split_rows), patch.object(
            map_guides_to_sheet,
            "build_rows_from_annual_plan",
            return_value=annual_rows,
        ):
            rows = map_guides_to_sheet.generate_general_data("?섑븰", "?섑븰", max_unit=6, grade_str="3-1")

        self.assertEqual(rows, split_rows)


if __name__ == "__main__":
    unittest.main()
