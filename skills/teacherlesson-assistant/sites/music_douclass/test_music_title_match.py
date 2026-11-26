"""music_helper 의 이름 맞추기 — 엄격 규칙 먼저, 없을 때만 가장 비슷한 하나 (T82, 검토 반영)."""
import unittest

try:
    import music_helper
except ImportError as exc:  # selenium 이 없는 곳(CI 등)에서는 건너뜀 — music_helper 가 selenium 을 바로 불러옴
    raise unittest.SkipTest(f"music_helper 를 불러올 수 없어 건너뜀: {exc}")


def lesson(unit, title):
    return {"unit_title": unit, "title": title, "chapter": object()}


def found(lessons, unit_text, references):
    """find_adjacent_lesson(offset=0) 은 '찾은 차시 자신'을 돌려준다 → 어느 차시를 골랐는지 본다."""
    return music_helper.find_adjacent_lesson(lessons, unit_text, references, 0)


class StrictFirstTests(unittest.TestCase):
    def test_similar_previous_lesson_does_not_steal_exact_match(self):
        a = lesson("1. 만나요, 음악 시간", "[3차시] 위치 알아보기")
        b = lesson("1. 만나요, 음악 시간", "[4차시] 위치 찾아보기")
        self.assertIs(found([a, b], "1단원", ["위치 찾아보기"]), b)

    def test_similar_previous_lesson_in_long_title(self):
        a = lesson("1. 만나요, 음악 시간", "[5차시] 우리가 사는 곳의 장소를 표현해 볼까요")
        b = lesson("1. 만나요, 음악 시간", "[6차시] 우리가 사는 곳의 장소를 조사해 볼까요")
        self.assertIs(found([a, b], "1단원", ["우리가 사는 곳의 장소를 조사해 볼까요"]), b)

    def test_exact_unit_name_does_not_pick_shorter_previous_unit(self):
        a = lesson("1. 우리 지역의 모습", "[1차시] 지도 보기")
        b = lesson("2. 우리 지역의 모습과 변화", "[1차시] 변화 살펴보기")
        self.assertIs(found([a, b], "우리 지역의 모습과 변화", ["변화 살펴보기"]), b)
        self.assertEqual(music_helper.lessons_in_unit([a, b], "우리 지역의 모습과 변화"), [b])

    def test_strict_reference_wins_even_if_another_reference_is_fuzzy(self):
        a = lesson("1. 만나요, 음악 시간", "[3차시] 위치 알아보기")
        b = lesson("1. 만나요, 음악 시간", "[4차시] 위치 찾아보기")
        # 첫 후보는 b 를 정확히 가리키고, 둘째 후보는 a 와 비슷할 뿐이다 → 정확한 쪽(b)을 지킨다
        self.assertIs(found([a, b], "1단원", ["[4차시] 위치 찾아보기", "위치 알아 보기"]), b)

    def test_number_rules_unchanged(self):
        a = lesson("1. 만나요, 음악 시간", "[3~4차시] 구슬비")
        self.assertIs(found([a], "1단원", ["3차시"]), a)
        self.assertIsNone(found([a], "1단원", ["5차시"]))


class FallbackTests(unittest.TestCase):
    def test_unit_found_by_name_when_strict_finds_none(self):
        a = lesson("1. 만나요, 음악 시간", "[1차시] 노래 부르기")
        b = lesson("2. 함께해요, 리듬", "[1차시] 리듬 치기")
        self.assertIs(found([a, b], "만나요 음악시간", ["노래 부르기"]), a)

    def test_lesson_found_by_name_when_strict_finds_none(self):
        a = lesson("1. 만나요, 음악 시간", "[3~4차시] 구슬비 노래 부르기")
        self.assertIs(found([a], "1단원", ["구슬비 노래부르기"]), a)

    def test_other_lesson_number_is_not_rescued_by_name(self):
        a = lesson("1. 만나요, 음악 시간", "[3차시] 위치 알아보기")
        self.assertIsNone(found([a], "1단원", ["[4차시] 위치 알아보기"]))

    def test_different_name_is_not_found(self):
        a = lesson("1. 만나요, 음악 시간", "[3차시] 구슬비")
        self.assertIsNone(found([a], "1단원", ["민주주의와 시민"]))


class RuleUnchangedTests(unittest.TestCase):
    def test_unit_matches_strict(self):
        self.assertTrue(music_helper.unit_matches("1. 만나요, 음악 시간", "1단원"))
        self.assertFalse(music_helper.unit_matches("2. 함께해요, 리듬", "1단원"))
        self.assertFalse(music_helper.unit_matches("1. 만나요, 음악 시간", "만나요 음악시간"))

    def test_lesson_matches_strict(self):
        self.assertTrue(music_helper.lesson_matches("[3~4차시] 구슬비", "3차시"))
        self.assertFalse(music_helper.lesson_matches("[3~4차시] 구슬비", "5차시"))
        self.assertFalse(music_helper.lesson_matches("[4차시] 위치 찾아보기", "위치 알아보기"))


if __name__ == "__main__":
    unittest.main()
