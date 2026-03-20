import unittest

import social_guide_extract


class SocialGuideExtractTests(unittest.TestCase):
    def test_strip_textbook_pages(self):
        result = social_guide_extract.strip_textbook_pages(
            "우리가 사는 곳에 있는 여러 장소를 표현해 볼까요(사23~27p)"
        )

        self.assertEqual(result, "우리가 사는 곳에 있는 여러 장소를 표현해 볼까요")

    def test_build_output_filename(self):
        filename = social_guide_extract.build_output_filename(
            r"C:\guides\social_guide.pdf",
            "[6~7차시] 우리가 사는 곳에 있는 여러 장소를 표현해 볼까요(사23~27p)",
            unit_text="1",
        )

        self.assertEqual(
            filename,
            "social_guide_1단원_6~7차시_우리가 사는 곳에 있는 여러 장소를 표현해 볼까요_지도서발췌.pdf",
        )

    def test_build_search_targets_prefers_core_topic(self):
        targets = social_guide_extract.build_search_targets(
            "[6~7차시] 우리가 사는 곳에 있는 여러 장소를 표현해 볼까요(사23~27p)"
        )

        self.assertIn(
            social_guide_extract.normalize_search_text("우리가 사는 곳에 있는 여러 장소를 표현해 볼까요"),
            targets,
        )
        self.assertIn(social_guide_extract.normalize_search_text("6~7차시"), targets)


if __name__ == "__main__":
    unittest.main()
