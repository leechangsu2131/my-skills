"""social_class_helper 의 이름 맞추기에 title_match 가 붙은 것 시험 (T82)."""
import unittest

import social_class_helper


class SocialTitleMatchTests(unittest.TestCase):
    def test_unit_found_by_name_when_number_is_missing(self):
        self.assertTrue(social_class_helper.unit_matches("1. 우리 지역의 모습", "우리지역 모습"))
        self.assertFalse(social_class_helper.unit_matches("2. 민주주의와 시민", "우리지역 모습"))

    def test_unit_number_still_decides_first(self):
        self.assertTrue(social_class_helper.unit_matches("1. 우리 지역의 모습", "1단원"))
        self.assertFalse(social_class_helper.unit_matches("2. 민주주의와 시민", "1단원"))

    def test_lesson_found_by_name_without_number(self):
        title = "[6~7차시] 우리가 사는 곳에 있는 여러 장소를 표현해 볼까요(사23~27p)"
        self.assertTrue(social_class_helper.lesson_matches(title, "우리가 사는 곳에 있는 여러 장소를 표현해볼까요"))

    def test_same_name_in_other_lesson_number_is_not_mixed(self):
        self.assertFalse(social_class_helper.lesson_matches("[3차시] 위치 알아보기", "[4차시] 위치 알아보기"))

    def test_existing_number_and_exact_rules_unchanged(self):
        title = "[3차시] 위치 알아보기"
        self.assertTrue(social_class_helper.lesson_matches(title, title))
        self.assertTrue(social_class_helper.lesson_matches(title, "3차시"))
        self.assertTrue(social_class_helper.lesson_matches(title, "위치 알아보기"))
        self.assertFalse(social_class_helper.lesson_matches(title, "5차시"))

    def test_different_name_still_not_found(self):
        self.assertFalse(social_class_helper.lesson_matches("[3차시] 위치 알아보기", "민주주의와 시민"))


if __name__ == "__main__":
    unittest.main()
