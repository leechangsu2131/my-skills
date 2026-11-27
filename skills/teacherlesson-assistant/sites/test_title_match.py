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


class PlainKeyTests(unittest.TestCase):
    def test_only_spacing_and_symbols_are_dropped(self):
        self.assertEqual(tm.plain_key("1. 만나요, 음악 시간"), "1만나요음악시간")  # 번호는 남는다
        self.assertEqual(tm.plain_key("우리 지역의 모습!"), tm.plain_key("우리지역의 모습"))
        self.assertEqual(tm.plain_key(None), "")

    def test_digits_and_parenthesized_text_stay(self):
        self.assertNotEqual(tm.plain_key("노래 부르기(1)"), tm.plain_key("노래 부르기(2)"))
        self.assertNotEqual(tm.plain_key("[3차시] 위치"), tm.plain_key("위치"))
        # normalize_title 은 이 둘을 같게 보지만(숫자 든 괄호를 뺌), 자동으로 열 기준에서는 다르다
        self.assertEqual(tm.match_level("노래 부르기(1)", "노래 부르기(2)"), tm.SAME)


class ResolveTests(unittest.TestCase):
    TITLES = ["[3차시] 위치 알아보기", "[4차시] 위치 찾아보기"]

    def test_strict_hit_keeps_query_unchanged(self):
        self.assertEqual(tm.resolve_query("위치 찾아보기", self.TITLES, _strict), "위치 찾아보기")

    def test_only_spacing_and_symbols_differ_is_automatic(self):
        titles = ["만나요, 음악 시간", "함께해요, 리듬"]
        self.assertEqual(tm.resolve_query("만나요 음악시간", titles, _strict), "만나요, 음악 시간")  # confirm 없이도

    def test_other_differences_need_confirmation(self):
        titles = ["1. 만나요, 음악 시간", "2. 함께해요, 리듬"]  # 번호가 달라서 띄어쓰기·기호만의 차이가 아니다
        asked = []

        def yes(q, c, level):
            asked.append((q, c, level))
            return True

        self.assertEqual(tm.resolve_query("만나요 음악시간", titles, _strict), "만나요 음악시간")  # confirm 없음 → 안 바꿈
        self.assertEqual(tm.resolve_query("만나요 음악시간", titles, _strict, confirm=lambda *a: False), "만나요 음악시간")
        self.assertEqual(tm.resolve_query("만나요 음악시간", titles, _strict, confirm=yes), "1. 만나요, 음악 시간")
        self.assertEqual(asked, [("만나요 음악시간", "1. 만나요, 음악 시간", tm.SAME)])

    def test_contains_and_similar_are_asked_with_their_level(self):
        asked = []
        tm.resolve_query("구슬비 노래", ["구슬비 노래 부르기"], lambda t, q: False,
                         confirm=lambda q, c, lv: asked.append(lv) or False)
        tm.resolve_query("우리 지역의 인문환경 알아보기", ["우리 지역의 자연환경 알아보기"], lambda t, q: False,
                         confirm=lambda q, c, lv: asked.append(lv) or False)
        self.assertEqual(asked, [tm.CONTAINS, tm.SIMILAR])

    def test_no_candidate_keeps_query_and_never_asks(self):
        asked = []
        self.assertEqual(tm.resolve_query("민주주의와 시민", self.TITLES, _strict, confirm=lambda *a: asked.append(a) or True), "민주주의와 시민")
        self.assertEqual(asked, [])

    def test_empty_titles_keeps_query(self):
        self.assertEqual(tm.resolve_query("위치", [], _strict), "위치")
        self.assertEqual(tm.resolve_references([], self.TITLES, _strict), [])

    def test_references_keep_all_when_any_is_strict(self):
        refs = ["[4차시] 위치 찾아보기", "위치알아 보기"]
        self.assertEqual(tm.resolve_references(refs, self.TITLES, _strict), refs)

    def test_references_collapse_to_single_best_when_none_is_strict(self):
        titles = ["만나요, 음악 시간", "함께해요, 리듬"]
        refs = ["만나요 음악시간", "함께해요 리듬"]  # 둘 다 띄어쓰기·기호만 다름 → 먼저 나온 것
        self.assertEqual(tm.resolve_references(refs, titles, _strict), ["만나요, 음악 시간"])
        refs = ["만나요 음악시간", "리듬"]  # 둘째 '리듬' 이 엄격하게 맞으면 모두 그대로
        self.assertEqual(tm.resolve_references(refs, titles, _strict), refs)

    def test_plain_candidate_beats_a_closer_looking_one(self):
        titles = ["위치 찾아보기 활동", "위치 찾아 보기"]  # 둘째가 띄어쓰기만 다름
        self.assertEqual(tm.resolve_query("위치찾아보기", titles, lambda t, q: False), "위치 찾아 보기")

    def test_number_guard(self):
        titles = ["[3차시] 위치 알아보기"]
        no_strict = lambda t, q: False  # noqa: E731
        yes = lambda *a: True  # noqa: E731
        # 가드가 없으면 확인에서 '예' 하면 되살아난다 → 호출하는 쪽이 가드를 켜야 하는 이유
        self.assertEqual(tm.resolve_query("[4차시] 위치 알아보기", titles, no_strict, confirm=yes), "[3차시] 위치 알아보기")
        # 가드가 있으면 번호가 이미 '아니다'라고 한 것은 확인조차 하지 않는다
        self.assertEqual(tm.resolve_query("[4차시] 위치 알아보기", titles, no_strict, guard_numbers=True, confirm=yes), "[4차시] 위치 알아보기")

    def test_resolve_search_texts_unit_then_lesson(self):
        lessons = [
            {"unit_title": "1. 우리 지역의 모습", "title": "[1차시] 지도 보기"},
            {"unit_title": "2. 우리 지역의 모습과 변화", "title": "변화 살펴보기"},
        ]
        unit, refs = tm.resolve_search_texts(lessons, "우리 지역의 모습과 변화", ["변화 살펴보기"], _strict, _strict)
        self.assertEqual((unit, refs), ("우리 지역의 모습과 변화", ["변화 살펴보기"]))  # 엄격하게 맞으니 그대로

        # 띄어쓰기만 다르면 단원 → 그 단원 안의 차시 순으로 자동으로 바로잡는다
        unit, refs = tm.resolve_search_texts(lessons, "2. 우리지역의 모습과 변화", ["변화살펴 보기"], _strict, _strict)
        self.assertEqual(unit, "2. 우리 지역의 모습과 변화")
        self.assertEqual(refs, ["변화 살펴보기"])

    def test_resolve_search_texts_passes_kind_to_confirm(self):
        lessons = [{"unit_title": "1. 우리 지역의 모습", "title": "지도 그리기 활동"}]
        asked = []
        tm.resolve_search_texts(
            lessons, "우리 지역 모습", ["지도그리기"], _strict, _strict,
            confirm=lambda kind, q, c, lv: asked.append((kind, q, c)) or kind == "단원",  # 단원만 '예'
        )
        self.assertEqual([k for k, *_ in asked], ["단원", "차시"])
        self.assertEqual(asked[0][1:], ("우리 지역 모습", "1. 우리 지역의 모습"))


class ExactOrderTests(unittest.TestCase):
    def test_exact_name_goes_first_rest_keep_order(self):
        lessons = [
            {"unit_title": "1. 단원", "title": "우리 지역의 문화유산"},
            {"unit_title": "1. 단원", "title": "우리 지역의 문화"},
            {"unit_title": "1. 단원", "title": "우리 지역의 문화재"},
        ]
        self.assertEqual(tm.exact_order(lessons, "1단원", ["우리 지역의 문화"]), [1, 0, 2])
        self.assertEqual(tm.exact_order(lessons, "1단원", ["없는 이름"]), [0, 1, 2])  # 같은 것이 없으면 그대로
        self.assertEqual(tm.exact_order(lessons, "1단원", ["문화재", "우리 지역의 문화"]), [1, 0, 2])  # 여러 이름 중 하나라도

    def test_spacing_is_collapsed_but_not_removed(self):
        lessons = [{"unit_title": "u", "title": "가  나"}, {"unit_title": "u", "title": "가나"}]
        self.assertEqual(tm.exact_order(lessons, "u", ["가 나"]), [0, 1])

    def test_exact_unit_first(self):
        lessons = [
            {"unit_title": "우리 지역의 문화유산", "title": "차시"},
            {"unit_title": "우리 지역의 문화", "title": "차시"},
        ]
        self.assertEqual(tm.exact_order(lessons, "우리 지역의 문화", ["차시"]), [1, 0])

    def test_exact_first_for_pairs(self):
        pairs = [("A", "우리 지역의 문화유산"), ("B", None), ("C", "우리 지역의 문화")]
        self.assertEqual(tm.exact_first(pairs, "우리 지역의 문화"), ["C", "A", "B"])


class ConsoleConfirmTests(unittest.TestCase):
    def setUp(self):
        tm.reset_confirm_answers()
        self.addCleanup(tm.reset_confirm_answers)
        self.lines = []

    def run_confirm(self, answer, query="구슬비", candidate="구슬비 노래 부르기", level=tm.CONTAINS, kind="차시"):
        def ask(message):
            self.asked = getattr(self, "asked", 0) + 1
            if isinstance(answer, Exception):
                raise answer
            return answer

        return tm.console_confirm(kind, query, candidate, level, ask=ask, show=self.lines.append)

    def test_yes_variants(self):
        for answer in ("y", "Y", " yes ", "ㅇ", "예"):
            tm.reset_confirm_answers()
            with self.subTest(answer=answer):
                self.assertTrue(self.run_confirm(answer))

    def test_default_is_no(self):
        for answer in ("", "n", "아니오", "그냥", EOFError(), KeyboardInterrupt()):
            tm.reset_confirm_answers()
            with self.subTest(answer=repr(answer)):
                self.assertFalse(self.run_confirm(answer))

    def test_shows_what_will_be_opened(self):
        self.run_confirm("n", query="구슬비", candidate="구슬비 노래 부르기", level=tm.CONTAINS)
        text = "\n".join(self.lines)
        self.assertIn("구슬비", text)
        self.assertIn("구슬비 노래 부르기", text)
        self.assertIn("이름이 겹침", text)
        self.lines.clear()
        tm.reset_confirm_answers()
        self.run_confirm("n", level=tm.SIMILAR)
        self.assertIn("글자가 비슷함", "\n".join(self.lines))

    def test_same_question_is_asked_only_once(self):
        self.asked = 0
        self.assertTrue(self.run_confirm("y"))
        self.assertTrue(self.run_confirm("n"))  # 두 번째는 묻지 않고 첫 대답(예)을 쓴다
        self.assertEqual(self.asked, 1)
        self.assertTrue(self.run_confirm("y", candidate="다른 차시"))  # 후보가 다르면 새로 묻는다
        self.assertEqual(self.asked, 2)

    def test_a_no_is_remembered_too(self):
        self.asked = 0
        self.assertFalse(self.run_confirm("n"))
        self.assertFalse(self.run_confirm("y"))
        self.assertEqual(self.asked, 1)


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
