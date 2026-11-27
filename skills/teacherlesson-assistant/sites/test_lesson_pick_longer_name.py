"""차시 고르기: 이름이 더 긴 다른 차시·단원은 묻지 않고 열지 않는다 (ISSUE-005, 교사 결정 2026-11-27).

- 띄어쓰기만 다른 찾는 차시가 있으면 더 긴 이름보다 그것을 연다.
- 찾는 것은 없고 더 긴 이름만 있으면 '이걸 열까요?' 로 묻고, '예' 일 때만 연다.
- 번호·쪽 표시만 덧붙은 이름은 묻지 않고 연다.
브라우저를 쓰는 함수와 확인 질문은 mock 이고, 고르기는 도우미의 실제 함수를 부른다.
"""
import contextlib
import io
import pathlib
import sys
import types
import unittest
from unittest import mock

SITES = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(SITES), str(SITES / "music_douclass"), str(SITES / "social_class")]

import social_class_helper  # selenium 이 없어도 불러와짐
import title_match

try:
    import music_helper
except ImportError:  # 음악 도우미는 selenium 이 없으면 못 불러옴 → 음악 시험만 건너뜀
    music_helper = None


def lessons(*pairs):
    """(단원 이름, 차시 이름) 들을 도우미가 읽은 목록 모양으로. chapter 에는 순번을 넣는다."""
    return [{"unit_title": u, "title": t, "chapter": i} for i, (u, t) in enumerate(pairs)]


def pick_music(items, unit, title, ask):
    with mock.patch.object(music_helper, "prepare_lesson_page"), \
         mock.patch.object(music_helper, "collect_lessons", return_value=items), \
         mock.patch.object(music_helper, "prompt_input", ask), \
         contextlib.redirect_stdout(io.StringIO()):
        _, index = music_helper.find_lesson_position(None, unit, title)
    return None if index < 0 else index


def pick_social(items, unit, title, ask):
    names = ("ensure_live_driver", "prepare_lesson_page", "collect_lessons",
             "highlight_lesson", "clear_highlight", "find_resource_button")
    config = types.SimpleNamespace(resource_label="자료", resource_keywords=[], site_kind="iscream")
    with mock.patch.multiple(social_class_helper, **{n: mock.DEFAULT for n in names}) as fake, \
         mock.patch.object(social_class_helper, "prompt_input", ask), \
         contextlib.redirect_stdout(io.StringIO()):
        fake["collect_lessons"].return_value = items
        fake["find_resource_button"].return_value = None
        social_class_helper.open_resource_for_lesson(object(), config, unit, title)
        called = fake["highlight_lesson"].call_args
    return None if called is None else called.args[1]


UNIT = "2. 우리 지역"
WANTED = "우리 지역의 문화"
LONGER = "우리 지역의 문화유산"   # 다른 차시
SPACED = "우리지역의 문화"        # 찾는 차시(띄어쓰기만 다름)
STUDY = "답사 계획 세우기"


class _Cases:
    picker = None

    def setUp(self):
        title_match.reset_confirm_answers()

    def pick(self, items, unit, title, answer=""):
        """(고른 순번 또는 None, 질문 횟수). answer 는 확인 질문에 하는 답."""
        title_match.reset_confirm_answers()
        ask = mock.Mock(return_value=answer)
        return self.picker(items, unit, title, ask), ask.call_count

    # 띄어쓰기만 다른 것이 있으면 그것을 연다
    def test_spacing_only_name_is_opened(self):
        self.assertEqual(self.pick(lessons((UNIT, SPACED)), UNIT, WANTED), (0, 0))

    def test_exact_name_wins_over_longer_name(self):
        self.assertEqual(self.pick(lessons((UNIT, LONGER), (UNIT, WANTED)), UNIT, WANTED), (1, 0))

    def test_spacing_only_lesson_wins_over_longer_name_in_either_order(self):
        self.assertEqual(self.pick(lessons((UNIT, LONGER), (UNIT, SPACED)), UNIT, WANTED), (1, 0))
        self.assertEqual(self.pick(lessons((UNIT, SPACED), (UNIT, LONGER)), UNIT, WANTED), (0, 0))

    def test_spacing_only_unit_wins_over_longer_unit_name(self):
        items = lessons((LONGER, STUDY), (SPACED, STUDY))
        self.assertEqual(self.pick(items, WANTED, STUDY), (1, 0))

    # 더 긴 이름만 있으면 묻는다
    def test_only_longer_lesson_is_asked_and_not_opened_by_default(self):
        self.assertEqual(self.pick(lessons((UNIT, LONGER)), UNIT, WANTED), (None, 1))

    def test_only_longer_lesson_opens_after_yes(self):
        self.assertEqual(self.pick(lessons((UNIT, LONGER)), UNIT, WANTED, "y"), (0, 1))

    def test_only_longer_unit_is_asked(self):
        items = lessons((LONGER, STUDY))
        self.assertEqual(self.pick(items, WANTED, STUDY), (None, 1))
        self.assertEqual(self.pick(items, WANTED, STUDY, "y"), (0, 1))

    def test_words_in_front_or_word_label_are_asked(self):
        for title in ("우리 고장의 위치 알아보기", "[심화] 위치 알아보기", "위치 알아보기 복습"):
            with self.subTest(title=title):
                self.assertEqual(self.pick(lessons((UNIT, title)), UNIT, "위치 알아보기"), (None, 1))

    # 번호·쪽 표시만 덧붙은 것은 묻지 않는다
    def test_number_and_page_marks_open_without_asking(self):
        for title in ("[3차시] 위치 알아보기", "3~4차시 위치 알아보기(사23~27p)", "[3~4차시] 위치 알아보기(사 23~27쪽)",
                      "1. 위치 알아보기", "위치 알아보기 (2)", "[3차시] 위치 알아보기!"):
            with self.subTest(title=title):
                self.assertEqual(self.pick(lessons((UNIT, title)), UNIT, "위치 알아보기"), (0, 0))

    def test_unit_with_leading_number_opens_without_asking(self):
        for unit in ("2. 우리 지역", "2단원 우리 지역", "[2단원] 우리 지역"):
            with self.subTest(unit=unit):
                self.assertEqual(self.pick(lessons((unit, STUDY)), "우리 지역", STUDY), (0, 0))

    def test_lesson_number_still_decides(self):
        items = lessons((UNIT, "[3차시] 위치 알아보기 활동"))
        self.assertEqual(self.pick(items, UNIT, "[3차시] 위치 알아보기"), (0, 0))


class MusicNameTests(unittest.TestCase):
    """음악 도우미의 다른 고르기 길(찾는 이름이 여럿)도 더 긴 이름은 확인 없이 고르지 않는다."""

    @unittest.skipIf(music_helper is None, "music_helper 를 불러올 수 없음(selenium 없음)")
    def test_adjacent_lesson_does_not_use_longer_name_without_confirmation(self):
        items = lessons((UNIT, LONGER), (UNIT, "다음 차시"))
        refs = [WANTED, "우리 지역 문화"]
        title_match.reset_confirm_answers()
        self.assertIsNone(music_helper.find_adjacent_lesson(items, UNIT, refs, 1, confirm=lambda *a: False))
        found = music_helper.find_adjacent_lesson(items, UNIT, refs, 1, confirm=lambda *a: True)
        self.assertEqual(found["title"], "다음 차시")


@unittest.skipIf(music_helper is None, "music_helper 를 불러올 수 없음(selenium 없음)")
class MusicTests(_Cases, unittest.TestCase):
    picker = staticmethod(pick_music)


class SocialTests(_Cases, unittest.TestCase):
    picker = staticmethod(pick_social)


if __name__ == "__main__":
    unittest.main()
