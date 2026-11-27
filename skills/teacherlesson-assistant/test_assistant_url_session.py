"""assistant_server.py 의 '열 수 있는 주소 확인'과 '저장 기록이 지금 수업과 맞는지 확인' 시험 (S1).

    python -m unittest test_assistant_url_session -v      (이 폴더에서)

표준 라이브러리만 쓰고 임시 폴더만 쓴다(내 문서의 실제 데이터·노트북 목록은 읽지 않음).
다루는 함수: ai_sites, allowed_urls, check_site_url, session_matches_lesson, saved_mismatch_info
"""
import json
import pathlib
import sys
import tempfile
import unittest
from datetime import date

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import assistant_server as app  # noqa: E402

NB = "https://notebooklm.google.com/notebook/abc"


class UrlTestBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self._tmp.name)
        self._saved = app.data_dir
        app.data_dir = lambda skill, *a, **k: self.root / skill   # 실제 내 문서 대신 임시 폴더

    def tearDown(self):
        app.data_dir = self._saved
        self._tmp.cleanup()

    def write_registry(self, reg):
        d = self.root / "util-notebooklm"
        d.mkdir(parents=True, exist_ok=True)
        (d / "notebooks.json").write_text(json.dumps(reg, ensure_ascii=False), encoding="utf-8")


class AiSitesTest(unittest.TestCase):
    def test_config_list_wins(self):
        mine = [{"name": "내사이트", "url": "https://example.com/"}]
        self.assertEqual(app.ai_sites({"ai_sites": mine}), mine)

    def test_missing_or_empty_falls_back_to_defaults(self):
        self.assertEqual(app.ai_sites({}), app.DEFAULT_AI_SITES)
        self.assertEqual(app.ai_sites({"ai_sites": []}), app.DEFAULT_AI_SITES)


class AllowedUrlsTest(UrlTestBase):
    def test_collects_every_config_source_and_drops_empty(self):
        cfg = {
            "subjects": {"수학": {"site": "https://math.example/", "notebooklm": NB}, "국어": {"site": ""}},
            "links": [{"url": "https://link.example/"}, {"name": "주소 없음"}],
            "hiclass_url": "https://hiclass.example/",
            "ai_sites": [{"url": "https://ai.example/"}],
        }
        urls = app.allowed_urls(cfg)
        self.assertEqual(urls, {"https://math.example/", NB, "https://link.example/",
                                "https://hiclass.example/", "https://ai.example/"})
        self.assertNotIn("", urls)

    def test_empty_config_still_allows_default_ai_sites(self):
        self.assertEqual(app.allowed_urls({}), {s["url"] for s in app.DEFAULT_AI_SITES})

    def test_registry_notebooks_only_for_lesson_topics_on_notebooklm(self):
        self.write_registry({
            "수업-수학": {"url": NB},
            "수업-국어": {"url": "https://evil.example/x"},      # notebooklm 주소가 아니면 빠짐
            "공문": {"url": "https://notebooklm.google.com/notebook/other"},   # '수업-' 로 안 시작하면 빠짐
        })
        urls = app.allowed_urls({})
        self.assertIn(NB, urls)
        self.assertNotIn("https://evil.example/x", urls)
        self.assertNotIn("https://notebooklm.google.com/notebook/other", urls)

    def test_broken_registry_is_ignored(self):
        d = self.root / "util-notebooklm"
        d.mkdir(parents=True)
        (d / "notebooks.json").write_text("{깨진 글", encoding="utf-8")
        self.assertEqual(app.allowed_urls({}), {s["url"] for s in app.DEFAULT_AI_SITES})
        self.write_registry(["목록이 아니라 배열"])
        self.assertEqual(app.allowed_urls({}), {s["url"] for s in app.DEFAULT_AI_SITES})


class CheckSiteUrlTest(UrlTestBase):
    CFG = {"links": [{"url": "https://link.example/page"}], "hiclass_url": "http://hiclass.example/"}

    def test_listed_http_and_https_pass_through_unchanged(self):
        self.assertEqual(app.check_site_url("https://link.example/page", self.CFG), "https://link.example/page")
        self.assertEqual(app.check_site_url("http://hiclass.example/", self.CFG), "http://hiclass.example/")

    def test_unlisted_url_is_rejected(self):
        for url in ("https://link.example/other", "https://link.example/page/", "https://evil.example/"):
            with self.assertRaises(ValueError, msg=url):
                app.check_site_url(url, self.CFG)

    def test_non_http_schemes_are_rejected_even_if_listed(self):
        for url in ("file:///C:/Windows/win.ini", "javascript:alert(1)", "ftp://x.example/"):
            cfg = {"links": [{"url": url}]}
            with self.assertRaises(ValueError, msg=url):
                app.check_site_url(url, cfg)

    def test_empty_and_none_are_rejected(self):
        for url in ("", None):
            with self.assertRaises(ValueError, msg=repr(url)):
                app.check_site_url(url, self.CFG)


class SessionMatchesLessonTest(unittest.TestCase):
    DAY = date(2026, 11, 27)
    LESSON = {"period": 3, "subject": "수학", "record_key": "K1"}

    def saved(self, **over):
        base = {"date": "2026-11-27", "period": 3, "subject": "수학", "record_key": "K1"}
        base.update(over)
        return base

    def test_exact_match(self):
        self.assertTrue(app.session_matches_lesson(self.saved(), self.DAY, self.LESSON))

    def test_old_record_without_info_is_trusted(self):
        self.assertTrue(app.session_matches_lesson({}, self.DAY, self.LESSON))
        self.assertTrue(app.session_matches_lesson({"date": "", "period": None}, self.DAY, self.LESSON))

    def test_nothing_to_compare_on_lesson_side_is_trusted(self):
        self.assertTrue(app.session_matches_lesson(self.saved(subject="국어"), self.DAY, {}))

    def test_different_value_means_other_lesson(self):
        for over in ({"date": "2026-11-26"}, {"subject": "국어"}, {"record_key": "K2"}, {"period": 4}):
            self.assertFalse(app.session_matches_lesson(self.saved(**over), self.DAY, self.LESSON), over)

    def test_period_compares_by_number_not_text(self):
        self.assertTrue(app.session_matches_lesson(self.saved(period="3교시"), self.DAY, self.LESSON))
        self.assertTrue(app.session_matches_lesson(self.saved(period=3), self.DAY, {**self.LESSON, "period": "3교시"}))
        self.assertFalse(app.session_matches_lesson(self.saved(period="4교시"), self.DAY, self.LESSON))

    def test_non_dict_saved_is_never_a_match(self):
        for bad in (None, "문자", [1], 3):
            self.assertFalse(app.session_matches_lesson(bad, self.DAY, self.LESSON), repr(bad))


class SavedMismatchInfoTest(unittest.TestCase):
    def test_picks_three_fields(self):
        saved = {"record_key": "K1", "lesson": "5차시", "title": "분수", "memo": "다른 글"}
        self.assertEqual(app.saved_mismatch_info(saved), {"record_key": "K1", "lesson": "5차시", "title": "분수"})

    def test_missing_fields_and_non_dict_give_empty_strings(self):
        empty = {"record_key": "", "lesson": "", "title": ""}
        self.assertEqual(app.saved_mismatch_info({}), empty)
        self.assertEqual(app.saved_mismatch_info(None), empty)
        self.assertEqual(app.saved_mismatch_info("문자"), empty)


if __name__ == "__main__":
    unittest.main()
