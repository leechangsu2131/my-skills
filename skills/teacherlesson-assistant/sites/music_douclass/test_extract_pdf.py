import os
import unittest

try:
    import extract_pdf
except (ImportError, SystemExit) as exc:  # PyMuPDF 가 없으면 extract_pdf 가 바로 종료함 → 건너뜀
    raise unittest.SkipTest(f"extract_pdf 를 불러올 수 없어 건너뜀: {exc}")


class ExtractPdfTests(unittest.TestCase):
    def test_build_output_filename_includes_unit_and_lesson(self):
        filename = extract_pdf.build_output_filename(
            os.path.join("지도서", "music.pdf"),  # 윈도우 경로 글자(C:\...)는 리눅스에서 폴더 구분으로 안 읽힘 → 현재 OS 방식으로
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
