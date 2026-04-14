import unittest
from pathlib import Path
from unittest.mock import patch

import map_guides_to_sheet


class MapGuidesToSheetTests(unittest.TestCase):
    def test_find_best_pdf_uses_exact_moral_filename_mapping(self):
        fake_pdfs = [
            Path(r"C:\fake\도덕3_1_1_지도서.pdf"),
            Path(r"C:\fake\도덕3_2_3_지도서.pdf"),
            Path(r"C:\fake\도덕3_2_4_지도서.pdf"),
        ]

        with patch.object(map_guides_to_sheet, "iter_search_pdfs", return_value=fake_pdfs):
            pdf_path = map_guides_to_sheet.find_best_pdf("도덕", 2, 3, grade_str="3")

        self.assertTrue(pdf_path.endswith("도덕3_2_3_지도서.pdf"))

    def test_find_best_pdf_uses_exact_korean_unit_pdf(self):
        fake_pdfs = [
            Path(r"C:\fake\국어3-1지도서_1.pdf"),
            Path(r"C:\fake\국어3-1지도서_2_1.pdf"),
            Path(r"C:\fake\국어3-1지도서_2_독서.pdf"),
        ]

        with patch.object(map_guides_to_sheet, "iter_search_pdfs", return_value=fake_pdfs):
            pdf_path = map_guides_to_sheet.find_best_pdf("국어", 1, 3, grade_str="3-1")
            reading_path = map_guides_to_sheet.find_best_pdf("국어", "독서", 5, grade_str="3-1")

        self.assertTrue(pdf_path.endswith("국어3-1지도서_2_1.pdf"))
        self.assertTrue(reading_path.endswith("국어3-1지도서_2_독서.pdf"))

    def test_parse_korean_overview_lines_sorts_ranges_and_maps_titles(self):
        lines = [
            "단원의 름",
            "배울 내용 살펴보기",
            "2. 표정과 몸짓, 목소리나 말투로",
            "표현하기",
            "1. 감각적 표현의 재미를 느끼며",
            "시 감상하기",
            "1차시",
            "11~12차시",
            "13차시",
            "2~5차시",
            "6~10차시",
            "배운 내용 실천하기",
            "마무리하기",
        ]

        lesson_ranges, titles = map_guides_to_sheet.parse_korean_overview_lines(lines)

        self.assertEqual(lesson_ranges, ["1", "2~5", "6~10", "11~12", "13"])
        self.assertEqual(titles["1"], "배울 내용 살펴보기")
        self.assertEqual(titles["2~5"], "감각적 표현의 재미를 느끼며 시 감상하기")
        self.assertEqual(titles["6~10"], "표정과 몸짓, 목소리나 말투로 표현하기")
        self.assertEqual(titles["11~12"], "배운 내용 실천하기")
        self.assertEqual(titles["13"], "마무리하기")

    def test_parse_korean_detail_page_blocks_reads_left_top_objective(self):
        blocks = [
            (68.0, 28.3, 120.0, 35.0, "감각적 표현의 재미를\n느끼며 시 감상하기", 0, 0),
            (211.4, 30.7, 260.0, 35.0, "2~3차시 / 13차시", 0, 0),
            (61.4, 74.9, 170.0, 82.0, "감각적 표현을 이해할 수 있다.\n학습 목표", 0, 0),
            (87.9, 110.7, 130.0, 118.0, "수업의 흐름", 0, 0),
        ]

        entry = map_guides_to_sheet.parse_korean_detail_page_blocks(blocks)

        self.assertEqual(entry["lesson_range"], "2~3")
        self.assertEqual(entry["소단원"], "감각적 표현의 재미를 느끼며 시 감상하기")
        self.assertEqual(entry["수업내용"], "감각적 표현을 이해할 수 있다.")

    def test_parse_korean_detail_page_blocks_falls_back_to_lesson_header(self):
        blocks = [
            (68.0, 28.3, 220.0, 35.0, "감각적 표현의 재미를 느끼며 시 감상하기", 0, 0),
            (211.4, 30.7, 260.0, 35.0, "2~3차시 / 13차시", 0, 0),
            (61.4, 74.9, 100.0, 82.0, "학습 목표", 0, 0),
            (87.9, 110.7, 130.0, 118.0, "수업의 흐름", 0, 0),
        ]

        entry = map_guides_to_sheet.parse_korean_detail_page_blocks(blocks)

        self.assertEqual(entry["lesson_range"], "2~3")
        self.assertEqual(entry["수업내용"], "감각적 표현의 재미를 느끼며 시 감상하기")
        self.assertEqual(entry["소단원"], "감각적 표현의 재미를 느끼며 시 감상하기")

    def test_generate_korean_data_uses_detail_entries_for_content_and_range(self):
        def overview(unit_num):
            if unit_num == 1:
                return (
                    ["1", "2~3", "4"],
                    {
                        "1": "배울 내용 살펴보기",
                        "2~3": "감각적 표현의 재미를 느끼며 시 감상하기",
                        "4": "마무리하기",
                    },
                )
            return ([], {})

        def detail_entries(unit_num, overview_titles=None):
            if unit_num == 1:
                return {
                    "1": {"소단원": "배울 내용 살펴보기", "수업내용": "배울 내용을 살펴볼 수 있다."},
                    "2~3": {
                        "소단원": "감각적 표현의 재미를 느끼며 시 감상하기",
                        "수업내용": "감각적 표현을 이해할 수 있다.",
                    },
                    "4": {"소단원": "마무리하기", "수업내용": "배운 내용을 마무리할 수 있다."},
                }
            return {}

        with patch.object(map_guides_to_sheet, "extract_korean_overview", side_effect=overview):
            with patch.object(map_guides_to_sheet, "extract_korean_detail_entries", side_effect=detail_entries):
                rows = map_guides_to_sheet.generate_korean_data()

        unit_one_rows = [
            row
            for row in rows
            if row["과목"] == "국어" and row["대단원"] == map_guides_to_sheet.KOREAN_UNIT_NAMES[1]
        ]

        self.assertEqual(
            [(row["차시"], row["소단원"], row["수업내용"]) for row in unit_one_rows[:4]],
            [
                ("1", "배울 내용 살펴보기", "배울 내용을 살펴볼 수 있다."),
                ("2(2~3)", "감각적 표현의 재미를 느끼며 시 감상하기", "감각적 표현을 이해할 수 있다."),
                ("3(2~3)", "감각적 표현의 재미를 느끼며 시 감상하기", "감각적 표현을 이해할 수 있다."),
                ("4", "마무리하기", "배운 내용을 마무리할 수 있다."),
            ],
        )

    def test_build_row_for_headers_uses_boolean_false_for_fallback_done_column(self):
        headers = ["과목", "계획일", "차시", "수업내용", "대단원", ""]
        record = {
            "과목": "국어",
            "계획일": "",
            "차시": "1",
            "수업내용": "배울 내용을 살펴볼 수 있다.",
            "대단원": "1. 생생하게 표현해요",
            "실행여부": False,
        }

        row = map_guides_to_sheet.build_row_for_headers(headers, record)

        self.assertEqual(row[:5], ["국어", "", "1", "배울 내용을 살펴볼 수 있다.", "1. 생생하게 표현해요"])
        self.assertIs(row[5], False)


if __name__ == "__main__":
    unittest.main()
