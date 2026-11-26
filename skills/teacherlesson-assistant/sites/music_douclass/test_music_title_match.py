"""music_helper 의 이름 맞추기에 title_match 가 붙은 것 시험 (T82)."""
import unittest

try:
    import music_helper
except ImportError as exc:  # selenium 이 없는 곳(CI 등)에서는 건너뜀 — music_helper 가 selenium 을 바로 불러옴
    raise unittest.SkipTest(f"music_helper 를 불러올 수 없어 건너뜀: {exc}")


class MusicTitleMatchTests(unittest.TestCase):
    def test_unit_found_by_name_when_number_is_missing(self):
        self.assertTrue(music_helper.unit_matches("1. 만나요, 음악 시간", "만나요 음악시간"))
        self.assertFalse(music_helper.unit_matches("2. 함께해요, 리듬", "만나요 음악시간"))

    def test_unit_number_still_decides_first(self):
        self.assertTrue(music_helper.unit_matches("1. 만나요, 음악 시간", "1단원"))
        self.assertFalse(music_helper.unit_matches("2. 함께해요, 리듬", "1단원"))

    def test_lesson_found_by_name_without_number(self):
        title = "[3~4차시] 구슬비 노래 부르기"
        self.assertTrue(music_helper.lesson_matches(title, "구슬비 노래부르기"))
        self.assertTrue(music_helper.lesson_matches("[5차시] 위치 알아보기", "위치알아보기"))

    def test_same_name_in_other_lesson_number_is_not_mixed(self):
        self.assertFalse(music_helper.lesson_matches("[3차시] 위치 알아보기", "[4차시] 위치 알아보기"))
        self.assertTrue(music_helper.lesson_matches("[3차시] 위치 알아보기", "[3차시] 위치 알아보기"))

    def test_existing_number_rules_unchanged(self):
        self.assertTrue(music_helper.lesson_matches("[3~4차시] 구슬비", "3차시"))
        self.assertFalse(music_helper.lesson_matches("[3~4차시] 구슬비", "5차시"))

    def test_different_name_still_not_found(self):
        self.assertFalse(music_helper.lesson_matches("[3차시] 구슬비", "민주주의와 시민"))


if __name__ == "__main__":
    unittest.main()
