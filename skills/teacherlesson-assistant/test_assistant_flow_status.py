"""assistant_server.py 의 flow_candidates·safe_name·monitor_rects·prepare_status 시험 (S1).

    python -m unittest test_assistant_flow_status -v      (이 폴더에서)

표준 라이브러리만 쓰고 임시 폴더만 쓴다(내 문서의 실제 흐름·준비 상태 파일은 읽지 않음).
"""
import json
import pathlib
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import assistant_server as app  # noqa: E402
import prepare_lessons as pl  # noqa: E402


class SafeNameTest(unittest.TestCase):
    def test_unsafe_characters_and_spaces_become_one_underscore(self):
        self.assertEqual(app.safe_name('a/b\\c:d*e?f"g<h>i|j k'), "a_b_c_d_e_f_g_h_i_j_k")
        self.assertEqual(app.safe_name("분수의   덧셈"), "분수의_덧셈")

    def test_edges_are_trimmed_and_empty_becomes_x(self):
        self.assertEqual(app.safe_name("  /분수/  "), "분수")
        for empty in ("", "   ", "///", "?"):
            self.assertEqual(app.safe_name(empty), "x", repr(empty))

    def test_long_names_are_cut_to_80(self):
        self.assertEqual(len(app.safe_name("가" * 200)), 80)

    def test_non_string_is_turned_into_text(self):
        self.assertEqual(app.safe_name(123), "123")

    def test_path_climbing_is_not_possible(self):
        self.assertNotIn("/", app.safe_name("../../탈출"))
        self.assertNotIn("\\", app.safe_name("..\\..\\탈출"))


class FlowCandidatesTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._saved = app.FLOWS
        app.FLOWS = pathlib.Path(self._tmp.name) / "flows"

    def tearDown(self):
        app.FLOWS = self._saved
        self._tmp.cleanup()

    def test_record_key_comes_first_then_subject_and_title(self):
        got = app.flow_candidates({"record_key": "K 1", "subject": "수학", "title": "분수의 덧셈"})
        self.assertEqual(got, [app.FLOWS / "K_1.json", app.FLOWS / "수학__분수의_덧셈.json"])

    def test_only_the_parts_that_exist_are_listed(self):
        self.assertEqual(app.flow_candidates({"record_key": "K1"}), [app.FLOWS / "K1.json"])
        self.assertEqual(app.flow_candidates({"subject": "수학", "title": "분수"}), [app.FLOWS / "수학__분수.json"])
        self.assertEqual(app.flow_candidates({}), [])
        self.assertEqual(app.flow_candidates({"record_key": "", "title": ""}), [])

    def test_all_candidates_stay_inside_flows_folder(self):
        evil = {"record_key": "../../x", "subject": "../..", "title": "..\\..\\y"}
        for path in app.flow_candidates(evil):
            self.assertEqual(path.parent, app.FLOWS, path)


class MonitorRectsTest(unittest.TestCase):
    def test_without_windows_api_falls_back_to_one_full_hd_primary(self):
        # 이 시험은 윈도우가 아닌 곳(ctypes.windll 없음)에서만 의미가 있다. 윈도우면 실제 모니터를 돌려 주므로 모양만 본다.
        rects = app.monitor_rects()
        self.assertTrue(rects)
        for rect in rects:
            self.assertEqual(len(rect), 5)
            self.assertIsInstance(rect[4], bool)
        if not hasattr(__import__("ctypes"), "windll"):
            self.assertEqual(rects, [(0, 0, 1920, 1080, True)])

    def test_failure_inside_windows_api_also_falls_back(self):
        fake = mock.MagicMock()
        fake.windll.user32.EnumDisplayMonitors.side_effect = OSError("실패")
        with mock.patch.dict(sys.modules, {"ctypes": fake}):
            self.assertEqual(app.monitor_rects(), [(0, 0, 1920, 1080, True)])


class PrepareStatusTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = pathlib.Path(self._tmp.name) / "prepare_status.json"
        self._saved = pl.STATUS
        pl.STATUS = self.path

    def tearDown(self):
        pl.STATUS = self._saved
        self._tmp.cleanup()

    def write(self, data):
        self.path.write_text(json.dumps(data), encoding="utf-8")

    def test_no_file_means_not_running(self):
        self.assertEqual(app.prepare_status(), {"running": False})

    def test_broken_json_means_not_running(self):
        self.path.write_text("{깨진 글", encoding="utf-8")
        self.assertEqual(app.prepare_status(), {"running": False})

    def test_running_flag_in_file_alone_is_not_enough(self):
        # 시작 시각이 없으면(0) 너무 오래된 것으로 보고 '준비 중' 이 아님
        self.write({"running": True, "pid": 1})
        self.assertFalse(app.prepare_status()["running"])

    def test_recent_and_alive_is_running_and_other_fields_pass_through(self):
        self.write({"running": True, "pid": 4242, "started_ts": time.time() - 60, "done": 2, "total": 5})
        with mock.patch.object(pl, "pid_alive", return_value=True):
            got = app.prepare_status()
        self.assertTrue(got["running"])
        self.assertEqual((got["done"], got["total"]), (2, 5))

    def test_dead_process_is_not_running_even_if_file_says_so(self):
        self.write({"running": True, "pid": 4242, "started_ts": time.time() - 60})
        with mock.patch.object(pl, "pid_alive", return_value=False):
            self.assertFalse(app.prepare_status()["running"])

    def test_too_old_is_not_running_even_if_process_alive(self):
        self.write({"running": True, "pid": 4242, "started_ts": time.time() - pl.STALE_SECONDS - 5})
        with mock.patch.object(pl, "pid_alive", return_value=True):
            self.assertFalse(app.prepare_status()["running"])

    def test_finished_status_stays_not_running(self):
        self.write({"running": False, "started_ts": time.time(), "done": 5, "total": 5})
        with mock.patch.object(pl, "pid_alive", return_value=True):
            got = app.prepare_status()
        self.assertFalse(got["running"])
        self.assertEqual(got["done"], 5)

    @unittest.expectedFailure
    def test_status_file_that_is_not_an_object_should_not_crash(self):
        # 지금은 파일 내용이 JSON 목록 등 객체가 아니면 AttributeError (ISSUE-새). 고치면 이 시험이 '예상 밖 성공' 으로 실패해 알려 준다.
        self.path.write_text("[]", encoding="utf-8")
        self.assertEqual(app.prepare_status(), {"running": False})


if __name__ == "__main__":
    unittest.main()
