import unittest

import extract_pdf


class ExtractPdfTests(unittest.TestCase):
    def test_build_output_filename_includes_unit_and_lesson(self):
        filename = extract_pdf.build_output_filename(
            r"C:\Users\user\Documents\지도서\music.pdf",
            "[5~6차시] 구슬비",
            unit_text="1",
        )

        self.assertEqual(filename, "music_1단원_5~6차시_구슬비_추출본.pdf")

    def test_normalize_unit_label_from_full_unit_title(self):
        self.assertEqual(
            extract_pdf.normalize_unit_label("2. 느껴요, 음악의 아름다움"),
            "2단원",
        )


if __name__ == "__main__":
    unittest.main()
