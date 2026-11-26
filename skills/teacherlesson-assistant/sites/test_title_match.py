"""title_match.py 시험 (T82) — 글자만 비교하는 순수 함수라 사이트·selenium 이 필요 없다."""
import unittest

import title_match as tm


class NormalizeTitleTests(unittest.TestCase):
    def test_removes_label_page_mark_number_and_spaces(self):
        cases = [
            ("1. 만나요, 음악 시간", "만나요음악시간"),                  # 앞 번호·쉼표·띄어쓰기
            ("[3차시] 위치 알아보기", "위치알아보기"),                    # 대괄호 꼬리표
            ("3~4차시 위치 알아보기(사23~27p)", "위치알아보기"),          # 차시 범위·쪽 표시
            ("제2단원 우리 지역의 모습", "우리지역의모습"),               # 제N단원
            ("3D 프린팅", "3d프린팅"),                                    # 구분 글자 없는 숫자는 이름의 일부
            ("우리 (지역) 모습", "우리지역모습"),                         # 글자뿐인 괄호는 괄호만 뺀다
            ("  ", ""),
            (None, ""),
        ]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assertEqual(tm.normalize_title(raw), expected)

    def test_only_unit_number_becomes_empty(self):
        self.assertEqual(tm.normalize_title("1단원"), "")
        self.assertEqual(tm.normalize_title("3차시"), "")


class MatchLevelTests(unittest.TestCase):
    def test_same_after_cleanup(self):
        pairs = [
            ("1. 만나요, 음악 시간", "만나요 음악시간"),
            ("[3차시] 위치 알아보기", "3~4차시 위치 알아보기(사23~27p)"),
            ("[6~7차시] 우리가 사는 곳에 있는 여러 장소를 표현해 볼까요(사23~27p)", "우리가 사는 곳에 있는 여러 장소를 표현해 볼까요"),
            ("3D 프린팅", "3D프린팅"),
        ]
        for a, b in pairs:
            with self.subTest(a=a, b=b):
                self.assertEqual(tm.match_level(a, b), tm.SAME)
                self.assertEqual(tm.match_level(b, a), tm.SAME)  # 순서를 바꿔도 같다

    def test_contains(self):
        self.assertEqual(tm.match_level("구슬비", "구슬비 노래 부르기"), tm.CONTAINS)
        self.assertEqual(tm.match_level("민주주의와 시민", "민주주의와 시민의 역할"), tm.CONTAINS)

    def test_similar(self):
        self.assertEqual(tm.match_level("우리 지역의 모습", "우리지역 모습"), tm.SIMILAR)

    def test_different_names_do_not_match(self):
        pairs = [
            ("2. 함께해요, 리듬", "1. 만나요, 음악 시간"),
            ("위치 알아보기", "민주주의와 시민"),
            ("음악", "음악 시간"),      # 정리하고 남은 글자가 너무 짧으면 '포함'으로 보지 않는다
        ]
        for a, b in pairs:
            with self.subTest(a=a, b=b):
                self.assertIsNone(tm.match_level(a, b))

    def test_empty_never_matches(self):
        self.assertIsNone(tm.match_level("", "만나요"))
        self.assertIsNone(tm.match_level("1단원", "1. 만나요"))  # 번호만 있으면 이름 비교를 하지 않는다(번호는 호출하는 쪽이 본다)
        self.assertFalse(tm.titles_match(None, "만나요"))

    def test_threshold_can_be_raised(self):
        self.assertIsNone(tm.match_level("우리 지역의 모습", "우리지역 모습", threshold=0.95))


class BestMatchTests(unittest.TestCase):
    CANDIDATES = ["[1차시] 지도", "[3차시] 위치 알아보기", "[5차시] 위치"]

    def test_picks_same_over_contains(self):
        item, level = tm.best_match("위치알아보기", self.CANDIDATES)
        self.assertEqual(item, "[3차시] 위치 알아보기")
        self.assertEqual(level, tm.SAME)

    def test_no_candidate_returns_none(self):
        self.assertIsNone(tm.best_match("민주주의", self.CANDIDATES))
        self.assertIsNone(tm.best_match("위치", []))

    def test_key_function_and_tie_keeps_first(self):
        rows = [{"id": 1, "t": "1. 만나요 음악시간"}, {"id": 2, "t": "만나요, 음악 시간"}]
        item, level = tm.best_match("만나요 음악 시간", rows, key=lambda r: r["t"])
        self.assertEqual(item["id"], 1)
        self.assertEqual(level, tm.SAME)


class LessonNumberTests(unittest.TestCase):
    def test_label_numbers(self):
        self.assertEqual(tm.lesson_label_numbers("[3~4차시] 위치"), ["3", "4"])
        self.assertEqual(tm.lesson_label_numbers("3차시"), ["3"])
        self.assertEqual(tm.lesson_label_numbers("위치 알아보기"), [])
        self.assertEqual(tm.lesson_label_numbers(None), [])

    def test_numbers_can_decide_only_when_both_have_numbers(self):
        self.assertTrue(tm.numbers_can_decide("[3차시] 위치", "[4차시] 위치"))
        self.assertTrue(tm.numbers_can_decide("[3차시] 위치", "3차시"))
        self.assertFalse(tm.numbers_can_decide("[3차시] 위치", "위치"))
        self.assertFalse(tm.numbers_can_decide("위치", "[3차시] 위치"))


if __name__ == "__main__":
    unittest.main()
