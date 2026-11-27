"""차시 고르기: 띄어쓰기만 다른 차시가 있는데 더 긴 이름의 다른 차시가 열리는 문제 재현 (ISSUE-005).

`expectedFailure` 두 묶음은 지금의 잘못된 동작을 적어 둔 것이다. 고치면 'unexpected success' 로 알려 주므로
그때 표시를 지운다. 표시 없는 시험은 이 시험 틀이 실제로 차시를 고른다는 것을 확인한다.
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

try:
    import music_helper
    import social_class_helper
    import title_match
except ImportError as exc:  # selenium 이 없는 곳에서는 건너뜀
    raise unittest.SkipTest(f"도우미를 불러올 수 없어 건너뜀: {exc}")


def lessons(*pairs):
    """(단원 이름, 차시 이름) 들을 도우미가 읽은 목록 모양으로. chapter 에는 순번을 넣는다."""
    return [{"unit_title": u, "title": t, "chapter": i} for i, (u, t) in enumerate(pairs)]


def pick_music(items, unit, title):
    with mock.patch.object(music_helper, "prepare_lesson_page"), \
         mock.patch.object(music_helper, "collect_lessons", return_value=items), \
         mock.patch.object(music_helper, "prompt_input", return_value=""), \
         contextlib.redirect_stdout(io.StringIO()):
        _, index = music_helper.find_lesson_position(None, unit, title)
    return None if index < 0 else index


def pick_social(items, unit, title):
    names = ("ensure_live_driver", "prepare_lesson_page", "collect_lessons",
             "highlight_lesson", "clear_highlight", "find_resource_button")
    config = types.SimpleNamespace(resource_label="자료", resource_keywords=[], site_kind="iscream")
    with mock.patch.multiple(social_class_helper, **{n: mock.DEFAULT for n in names}) as fake, \
         mock.patch.object(social_class_helper, "prompt_input", return_value=""), \
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


class _Cases:
    pick = None

    def setUp(self):
        title_match.reset_confirm_answers()

    def test_control_spacing_only_name_is_opened(self):
        self.assertEqual(self.pick(lessons((UNIT, SPACED)), UNIT, WANTED), 0)

    def test_control_exact_name_wins_over_longer_name(self):
        self.assertEqual(self.pick(lessons((UNIT, LONGER), (UNIT, WANTED)), UNIT, WANTED), 1)


class MusicTests(_Cases, unittest.TestCase):
    pick = staticmethod(pick_music)

    @unittest.expectedFailure
    def test_spacing_only_lesson_wins_over_longer_name(self):
        self.assertEqual(self.pick(lessons((UNIT, LONGER), (UNIT, SPACED)), UNIT, WANTED), 1)

    @unittest.expectedFailure
    def test_spacing_only_unit_wins_over_longer_unit_name(self):
        items = lessons((LONGER, "답사 계획 세우기"), (SPACED, "답사 계획 세우기"))
        self.assertEqual(self.pick(items, WANTED, "답사 계획 세우기"), 1)


class SocialTests(_Cases, unittest.TestCase):
    pick = staticmethod(pick_social)

    @unittest.expectedFailure
    def test_spacing_only_lesson_wins_over_longer_name(self):
        self.assertEqual(self.pick(lessons((UNIT, LONGER), (UNIT, SPACED)), UNIT, WANTED), 1)

    @unittest.expectedFailure
    def test_spacing_only_unit_wins_over_longer_unit_name(self):
        items = lessons((LONGER, "답사 계획 세우기"), (SPACED, "답사 계획 세우기"))
        self.assertEqual(self.pick(items, WANTED, "답사 계획 세우기"), 1)


if __name__ == "__main__":
    unittest.main()
