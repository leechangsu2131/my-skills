from pathlib import Path
from uuid import uuid4

import unittest

import music_helper


class MusicHelperLogicTests(unittest.TestCase):
    def test_unit_matches_by_number(self):
        self.assertTrue(music_helper.unit_matches("1. 만나요, 음악 시간", "1단원"))
        self.assertFalse(music_helper.unit_matches("2. 함께해요, 리듬", "1단원"))

    def test_find_adjacent_lesson_stays_in_same_unit(self):
        lessons = [
            {"unit_title": "1. 만나요, 음악 시간", "title": "[1~2차시] 새 친구들과 함께"},
            {"unit_title": "1. 만나요, 음악 시간", "title": "[3~4차시] 길고 짧은 음, 높고 낮은 음"},
            {"unit_title": "1. 만나요, 음악 시간", "title": "[5~6차시] 구슬비"},
            {"unit_title": "2. 즐겨요, 음악 놀이", "title": "[1~2차시] 다른 단원 첫 차시"},
        ]

        result = music_helper.find_adjacent_lesson(lessons, "1단원", ["3차시"], 1)

        self.assertIsNotNone(result)
        self.assertEqual(result["unit_title"], "1. 만나요, 음악 시간")
        self.assertEqual(result["title"], "[5~6차시] 구슬비")

    def test_find_adjacent_lesson_moves_to_next_unit_at_unit_end(self):
        lessons = [
            {"unit_title": "1. 만나요, 음악 시간", "title": "[1~2차시] 새 친구들과 함께"},
            {"unit_title": "1. 만나요, 음악 시간", "title": "[3~4차시] 길고 짧은 음, 높고 낮은 음"},
            {"unit_title": "2. 즐겨요, 음악 놀이", "title": "[1~2차시] 다른 단원 첫 차시"},
        ]

        result = music_helper.find_adjacent_lesson(lessons, "1단원", ["3차시"], 1)

        self.assertIsNotNone(result)
        self.assertEqual(result["unit_title"], "2. 즐겨요, 음악 놀이")
        self.assertEqual(result["title"], "[1~2차시] 다른 단원 첫 차시")

    def test_lesson_reference_candidates_prefers_exact_title(self):
        result = music_helper.lesson_reference_candidates(
            "3차시", "[3~4차시] 길고 짧은 음, 높고 낮은 음"
        )

        self.assertEqual(result[0], "[3~4차시] 길고 짧은 음, 높고 낮은 음")
        self.assertEqual(result[1], "3차시")

    def test_list_guide_pdfs_reads_default_folder(self):
        test_dir = Path(__file__).parent / f"guide_test_{uuid4().hex}"
        test_dir.mkdir(exist_ok=True)
        original_dir = music_helper.DEFAULT_GUIDE_DIR
        try:
            music_helper.DEFAULT_GUIDE_DIR = test_dir
            (test_dir / "b.pdf").write_text("x", encoding="utf-8")
            (test_dir / "a.pdf").write_text("x", encoding="utf-8")
            (test_dir / "note.txt").write_text("x", encoding="utf-8")

            result = music_helper.list_guide_pdfs()

            self.assertEqual([path.name for path in result], ["a.pdf", "b.pdf"])
        finally:
            for file_path in test_dir.glob("*"):
                file_path.unlink(missing_ok=True)
            test_dir.rmdir()
            music_helper.DEFAULT_GUIDE_DIR = original_dir


if __name__ == "__main__":
    unittest.main()
