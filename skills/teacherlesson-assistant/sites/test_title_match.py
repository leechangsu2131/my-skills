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
            ("1-2. 만나요", "만나요"),                                    # 앞 번호가 범위여도 통째로(검토 🟡)
            ("3~4. 구슬비", "구슬비"),
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


def _strict(title, query):
    """시험용 엄격 규칙(도우미의 기존 규칙처럼): 공백만 정리한 찾는 이름이 제목 안에 글자 그대로 들어 있을 때만.
    쉼표·괄호까지 지우지 않는다 — 그건 title_match 의 '같음'이 하는 일이다."""
    q = " ".join((query or "").split())
    return bool(q) and q in " ".join((title or "").split())


class ResolveTests(unittest.TestCase):
    TITLES = ["[3차시] 위치 알아보기", "[4차시] 위치 찾아보기"]

    def test_strict_hit_keeps_query_unchanged(self):
        self.assertEqual(tm.resolve_query("위치 찾아보기", self.TITLES, _strict), "위치 찾아보기")

    def test_fallback_replaces_with_site_title(self):
        # 엄격하게는 하나도 안 맞고(쉼표·띄어쓰기), 이름이 같은 하나가 있으면 그 제목으로
        titles = ["1. 만나요, 음악 시간", "2. 함께해요, 리듬"]
        self.assertEqual(tm.resolve_query("만나요 음악시간", titles, _strict), "1. 만나요, 음악 시간")

    def test_no_candidate_keeps_query(self):
        self.assertEqual(tm.resolve_query("민주주의와 시민", self.TITLES, _strict), "민주주의와 시민")

    def test_empty_titles_keeps_query(self):
        self.assertEqual(tm.resolve_query("위치", [], _strict), "위치")
        self.assertEqual(tm.resolve_references([], self.TITLES, _strict), [])

    def test_references_keep_all_when_any_is_strict(self):
        refs = ["[4차시] 위치 찾아보기", "위치알아 보기"]
        self.assertEqual(tm.resolve_references(refs, self.TITLES, _strict), refs)

    def test_references_collapse_to_single_best_when_none_is_strict(self):
        titles = ["1. 만나요, 음악 시간", "2. 함께해요, 리듬"]
        refs = ["만나요 음악시간", "함께해요 리듬"]  # 둘 다 쉼표 때문에 엄격하게는 안 맞고, 이름은 같음 → 먼저 나온 것
        self.assertEqual(tm.resolve_references(refs, titles, _strict), ["1. 만나요, 음악 시간"])
        # 엄격하게 맞는 후보가 하나라도 있으면(둘째 '리듬') 모두 그대로 둔다
        refs = ["만나요 음악시간", "리듬"]
        self.assertEqual(tm.resolve_references(refs, titles, _strict), refs)

    def test_number_guard(self):
        titles = ["[3차시] 위치 알아보기"]
        self.assertEqual(tm.resolve_query("[4차시] 위치 알아보기", titles, lambda t, q: False, guard_numbers=True), "[4차시] 위치 알아보기")
        # 가드가 없으면 이름이 같아서 되살린다 → 호출하는 쪽이 가드를 켜야 하는 이유
        self.assertEqual(tm.resolve_query("[4차시] 위치 알아보기", titles, lambda t, q: False), "[3차시] 위치 알아보기")

    def test_resolve_search_texts_unit_then_lesson(self):
        lessons = [
            {"unit_title": "1. 우리 지역의 모습", "title": "[1차시] 지도 보기"},
            {"unit_title": "2. 우리 지역의 모습과 변화", "title": "[1차시] 변화 살펴보기"},
        ]

        unit, refs = tm.resolve_search_texts(lessons, "우리 지역의 모습과 변화", ["변화 살펴보기"], _strict, _strict)
        self.assertEqual((unit, refs), ("우리 지역의 모습과 변화", ["변화 살펴보기"]))  # 엄격하게 맞으니 그대로

        # 엄격하게 하나도 안 맞으면 단원 → 그 단원 안의 차시 순으로 사이트 이름으로 바로잡는다
        unit, refs = tm.resolve_search_texts(lessons, "우리지역 모습과 변화", ["변화살펴 보기"], _strict, _strict)
        self.assertEqual(unit, "2. 우리 지역의 모습과 변화")
        self.assertEqual(refs, ["[1차시] 변화 살펴보기"])


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
