"""social_class_helper.find_lesson_item — 엄격 규칙 먼저, 없을 때만 가장 비슷한 하나 (T82, 검토 반영)."""
import unittest

import social_class_helper as sc


def lesson(unit, title):
    return {"unit_title": unit, "title": title, "chapter": object()}


class StrictFirstTests(unittest.TestCase):
    """비슷한 이름이 앞에 있어도, 정확히 찾던 것은 예전처럼 정확히 찾는다."""

    def test_similar_previous_lesson_does_not_steal_exact_match(self):
        a = lesson("1. 우리 고장", "[3차시] 위치 알아보기")
        b = lesson("1. 우리 고장", "[4차시] 위치 찾아보기")
        self.assertIs(sc.find_lesson_item([a, b], "1단원", "위치 찾아보기"), b)

    def test_similar_previous_lesson_in_long_title(self):
        a = lesson("1. 우리 고장", "[5차시] 우리가 사는 곳의 장소를 표현해 볼까요")
        b = lesson("1. 우리 고장", "[6차시] 우리가 사는 곳의 장소를 조사해 볼까요")
        self.assertIs(sc.find_lesson_item([a, b], "1단원", "우리가 사는 곳의 장소를 조사해 볼까요"), b)

    def test_exact_unit_name_does_not_pick_shorter_previous_unit(self):
        a = lesson("1. 우리 지역의 모습", "[1차시] 지도 보기")
        b = lesson("2. 우리 지역의 모습과 변화", "[1차시] 변화 살펴보기")
        self.assertIs(sc.find_lesson_item([a, b], "우리 지역의 모습과 변화", "변화 살펴보기"), b)

    def test_number_rules_unchanged(self):
        a = lesson("1. 우리 고장", "[3차시] 위치 알아보기")
        b = lesson("1. 우리 고장", "[4차시] 위치 찾아보기")
        self.assertIs(sc.find_lesson_item([a, b], "1단원", "4차시"), b)
        self.assertIs(sc.find_lesson_item([a, b], "1단원", "[3차시] 위치 알아보기"), a)


class FallbackTests(unittest.TestCase):
    """엄격한 규칙으로 하나도 못 찾을 때만 이름이 비슷한 하나로 찾는다."""

    def test_lesson_found_when_only_spacing_and_marks_differ(self):
        a = lesson("1. 우리 고장", "[6~7차시] 우리가 사는 곳에 있는 여러 장소를 표현해 볼까요(사23~27p)")
        self.assertIs(sc.find_lesson_item([a], "1단원", "우리가 사는 곳에 있는 여러 장소를 표현해볼까요"), a)

    def test_unit_found_by_similar_name(self):
        a = lesson("1. 우리 지역의 모습", "[1차시] 지도 보기")
        b = lesson("2. 민주주의와 시민", "[1차시] 시민 알아보기")
        self.assertIs(sc.find_lesson_item([a, b], "우리지역 모습", "지도 보기"), a)

    def test_best_candidate_wins_not_first(self):
        a = lesson("1. 우리 고장", "[3차시] 위치 알아보기")
        b = lesson("1. 우리 고장", "[4차시] 위치 찾아 보기")
        # '위치찾아보기'(정리 후) 와 같은 것은 b 하나라 b
        self.assertIs(sc.find_lesson_item([a, b], "1단원", "위치찾아보기"), b)

    def test_other_lesson_number_is_not_rescued_by_name(self):
        a = lesson("1. 우리 고장", "[3차시] 위치 알아보기")
        self.assertIsNone(sc.find_lesson_item([a], "1단원", "[4차시] 위치 알아보기"))

    def test_different_name_is_not_found(self):
        a = lesson("1. 우리 고장", "[3차시] 위치 알아보기")
        self.assertIsNone(sc.find_lesson_item([a], "1단원", "민주주의와 시민"))

    def test_empty_list(self):
        self.assertIsNone(sc.find_lesson_item([], "1단원", "위치 알아보기"))


class RuleUnchangedTests(unittest.TestCase):
    """unit_matches·lesson_matches 자체는 원래 엄격 규칙 그대로다."""

    def test_unit_matches_strict(self):
        self.assertTrue(sc.unit_matches("1. 우리 지역의 모습", "1단원"))
        self.assertFalse(sc.unit_matches("2. 민주주의와 시민", "1단원"))
        self.assertFalse(sc.unit_matches("1. 우리 지역의 모습", "우리 지역의 모습과 변화"))
        self.assertFalse(sc.unit_matches("1. 우리 지역의 모습", "우리지역 모습"))

    def test_lesson_matches_strict(self):
        title = "[3차시] 위치 알아보기"
        self.assertTrue(sc.lesson_matches(title, title))
        self.assertTrue(sc.lesson_matches(title, "3차시"))
        self.assertTrue(sc.lesson_matches(title, "위치 알아보기"))
        self.assertFalse(sc.lesson_matches(title, "5차시"))
        self.assertFalse(sc.lesson_matches("[4차시] 위치 찾아보기", "위치 알아보기"))


if __name__ == "__main__":
    unittest.main()
