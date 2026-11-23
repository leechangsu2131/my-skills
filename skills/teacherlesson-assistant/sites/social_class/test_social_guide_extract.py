import unittest
from pathlib import Path
from unittest.mock import patch

import social_guide_extract


class FakePage:
    def __init__(self, text: str):
        self._text = text

    def get_text(self) -> str:
        return self._text


class FakeDocument:
    def __init__(self, pages: list[str]):
        self._pages = pages

    def __len__(self) -> int:
        return len(self._pages)

    def load_page(self, page_num: int) -> FakePage:
        return FakePage(self._pages[page_num])


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

    def test_build_unique_output_path_adds_number_suffix(self):
        original = Path(r"C:\guides\guide_extract.pdf")
        existing_paths = {
            str(original),
            str(original.with_name("guide_extract (1).pdf")),
        }

        def fake_exists(path: Path) -> bool:
            return str(path) in existing_paths

        with patch.object(type(original), "exists", autospec=True, side_effect=fake_exists):
            unique_path = social_guide_extract.build_unique_output_path(original)

        self.assertEqual(unique_path, original.with_name("guide_extract (2).pdf"))

    def test_build_search_targets_prefers_core_topic(self):
        targets = social_guide_extract.build_search_targets(
            "[6~7차시] 우리가 사는 곳에 있는 여러 장소를 표현해 볼까요(사23~27p)"
        )

        self.assertIn(
            social_guide_extract.normalize_search_text("우리가 사는 곳에 있는 여러 장소를 표현해 볼까요"),
            targets,
        )
        self.assertIn(social_guide_extract.normalize_search_text("6~7차시"), targets)

    def test_extract_textbook_pages(self):
        textbook_target = social_guide_extract.extract_textbook_pages(
            "[6~7차시] 우리가 사는 곳에 있는 여러 장소를 표현해 볼까요(사23~27p)"
        )

        self.assertEqual(textbook_target, social_guide_extract.normalize_search_text("교과서 23~27쪽"))

    def test_parse_lesson_range(self):
        self.assertEqual(social_guide_extract.parse_lesson_range("6~7차시"), (6, 7))
        self.assertEqual(social_guide_extract.parse_lesson_range("12차시"), (12, 12))

    def test_build_next_lesson_pattern_matches_next_bundle(self):
        pattern = social_guide_extract.build_next_lesson_pattern("6~7차시")

        self.assertIsNotNone(pattern)
        self.assertTrue(pattern.search("8~9차시"))
        self.assertTrue(pattern.search("8차시"))
        self.assertFalse(pattern.search("18차시"))

    def test_score_page_for_title_prefers_lesson_start_over_plan_page(self):
        exact_title = "[6~7차시] 우리가 사는 곳에 있는 여러 장소를 표현해 볼까요(사23~27p)"
        plan_page = "\n".join(
            [
                "단원의 지도 계획",
                "우리가 사는 곳의 여러 장소",
                "차시명",
                "주요 학습 내용",
                "학생 활동",
                "6~7차시 우리가 사는 곳에 있는 여러 장소를 표현해 볼까요",
                "23~27",
            ]
        )
        lesson_page = "\n".join(
            [
                "우리가 사는 곳에 있는 여러 장소를 표현해 볼까요",
                "교수학습 과정",
                "학습 목표",
                "차시 안내",
                "교과서 23~27쪽",
            ]
        )

        plan_score = social_guide_extract.score_page_for_title(plan_page, exact_title)
        lesson_score = social_guide_extract.score_page_for_title(lesson_page, exact_title)

        self.assertGreater(lesson_score, plan_score)

    def test_find_start_page_skips_plan_page_and_picks_lesson_start(self):
        exact_title = "[6~7차시] 우리가 사는 곳에 있는 여러 장소를 표현해 볼까요(사23~27p)"
        doc = FakeDocument(
            [
                "\n".join(
                    [
                        "단원의 지도 계획",
                        "우리가 사는 곳의 여러 장소",
                        "차시명",
                        "주요 학습 내용",
                        "학생 활동",
                        "6~7차시 우리가 사는 곳에 있는 여러 장소를 표현해 볼까요",
                        "23~27",
                    ]
                ),
                "\n".join(
                    [
                        "활동지",
                        "6~7차시",
                        "우리가 사는 곳의 여러 장소를 표현하는 활동",
                    ]
                ),
                "\n".join(
                    [
                        "우리가 사는 곳에 있는 여러 장소를 표현해 볼까요",
                        "교수학습 과정",
                        "학습 목표",
                        "차시 안내",
                        "교과서 23~27쪽",
                    ]
                ),
            ]
        )

        self.assertEqual(social_guide_extract.find_start_page(doc, exact_title), 2)

    def test_find_next_lesson_start_page_detects_next_bundle(self):
        exact_title = "[6~7차시] 우리가 사는 곳에 있는 여러 장소를 표현해 볼까요(사23~27p)"
        doc = FakeDocument(
            [
                "\n".join(
                    [
                        "우리가 사는 곳에 있는 여러 장소를 표현해 볼까요",
                        "교수학습 과정",
                        "학습 목표",
                        "차시 안내",
                        "교과서 23~27쪽",
                    ]
                ),
                "\n".join(
                    [
                        "학습 안내",
                        "그림으로 표현하기",
                        "차시 안내",
                    ]
                ),
                "\n".join(
                    [
                        "활동지",
                        "우리가 사는 곳의 여러 장소 표현 계획서 쓰기",
                    ]
                ),
                "\n".join(
                    [
                        "우리가 사는 곳에 있는 여러 장소를 소개해 볼까요",
                        "8~9차시",
                        "교수학습 과정",
                        "학습 목표",
                        "차시 안내",
                        "교과서 28~32쪽",
                    ]
                ),
            ]
        )

        self.assertEqual(social_guide_extract.find_next_lesson_start_page(doc, 0, exact_title), 3)

    def test_find_end_page_stops_before_next_lesson_start(self):
        exact_title = "[6~7차시] 우리가 사는 곳에 있는 여러 장소를 표현해 볼까요(사23~27p)"
        doc = FakeDocument(
            [
                "\n".join(
                    [
                        "우리가 사는 곳에 있는 여러 장소를 표현해 볼까요",
                        "교수학습 과정",
                        "학습 목표",
                        "차시 안내",
                    ]
                ),
                "학습 안내\n그림으로 표현하기",
                "활동지\n표현 계획서 쓰기",
                "\n".join(
                    [
                        "우리가 사는 곳에 있는 여러 장소를 소개해 볼까요",
                        "8~9차시",
                        "교수학습 과정",
                        "학습 목표",
                        "차시 안내",
                    ]
                ),
            ]
        )

        self.assertEqual(social_guide_extract.find_end_page(doc, 0, exact_title, extract_pages=4), 2)

    def test_find_end_page_falls_back_to_default_page_count_without_next_lesson(self):
        exact_title = "[6~7차시] 우리가 사는 곳에 있는 여러 장소를 표현해 볼까요(사23~27p)"
        doc = FakeDocument(
            [
                "\n".join(
                    [
                        "우리가 사는 곳에 있는 여러 장소를 표현해 볼까요",
                        "교수학습 과정",
                        "학습 목표",
                        "차시 안내",
                    ]
                ),
                "학습 안내\n그림으로 표현하기",
                "활동지\n표현 계획서 쓰기",
                "참고 자료\n심상지도",
                "추가 자료",
            ]
        )

        self.assertEqual(social_guide_extract.find_end_page(doc, 0, exact_title, extract_pages=4), 3)


if __name__ == "__main__":
    unittest.main()
