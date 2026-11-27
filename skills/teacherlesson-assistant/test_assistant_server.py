"""assistant_server.py 의 수업 흐름 저장(POST /api/flow) 시험. 표준 라이브러리만 쓴다.

    python -m unittest test_assistant_server -v      (이 폴더에서)

임시 폴더만 쓰므로 내 문서의 실제 데이터(flows 등)는 건드리지 않는다.
"""
import http.client
import json
import pathlib
import sys
import tempfile
import threading
import unittest
from datetime import date
from http.server import ThreadingHTTPServer

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import assistant_server as app  # noqa: E402

STEP = {"name": "도입", "minutes": 5, "do": "지난 시간 떠올리기", "say": "무엇을 배웠나요?", "tip": "앞 차시 확인"}


def body(**over):
    base = {"record_key": "K1", "subject": "수학", "title": "분수의 덧셈",
            "flow": {"goal": "분수를 더한다", "materials": "분수 막대, 딱지", "steps": [dict(STEP), {"name": "정리", "minutes": 5}]}}
    base.update(over)
    return base


class FlowTestBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.flows = pathlib.Path(self._tmp.name) / "flows"
        self.flows.mkdir()
        self._saved = (app.FLOWS, app.load_config)
        app.FLOWS = self.flows
        app.load_config = lambda: {"subjects": {"수학": {"publisher": "아이스크림"}}}

    def tearDown(self):
        app.FLOWS, app.load_config = self._saved
        self._tmp.cleanup()


class SessionPeriodIsolationTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._saved = (app.load_config, app.fetch_schedule, app.SESSIONS, app.CAUTIONS_PATH,
                       app.find_flow, app.find_unit, app.recent_memos)
        root = pathlib.Path(self._tmp.name)
        app.load_config = lambda: {"subjects": {"국어": {"publisher": "가출판"}}}
        app.fetch_schedule = lambda _cfg, _day: ([
            {"period": 1, "subject": "국어", "lesson": "1차시", "title": "첫 수업", "record_key": "K1"},
            {"period": 2, "subject": "국어", "lesson": "2차시", "title": "둘째 수업", "record_key": "K2"},
        ], "시험용 시간표")
        app.SESSIONS = root / "sessions"
        app.CAUTIONS_PATH = root / "publisher_notes.json"
        app.find_flow = lambda _lesson: None
        app.find_unit = lambda _lesson: None
        app.recent_memos = lambda _subject: []

    def tearDown(self):
        (app.load_config, app.fetch_schedule, app.SESSIONS, app.CAUTIONS_PATH,
         app.find_flow, app.find_unit, app.recent_memos) = self._saved
        self._tmp.cleanup()

    def test_period_two_does_not_receive_period_one_saved_timer(self):
        day = date(2026, 11, 27)
        first = {"date": day.isoformat(), "period": 1, "subject": "국어", "record_key": "K1",
                 "lesson": "1차시", "title": "첫 수업", "memos": [{"kind": "step", "idx": 2}]}
        wrong_second = {**first, "memos": [{"kind": "step", "idx": 0}]}
        for record_key, saved in (("K1", first), ("K2", wrong_second)):
            path = app.session_path(day.isoformat(), 1 if record_key == "K1" else 2, "국어", record_key)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")

        lessons = app.state(day)["lessons"]

        self.assertEqual(lessons[0]["saved"]["period"], 1)
        self.assertNotIn("saved", lessons[1])
        self.assertEqual(lessons[1]["saved_mismatch"]["record_key"], "K1")

    def test_period_two_keeps_its_own_saved_timer(self):
        day = date(2026, 11, 27)
        saved = {"date": day.isoformat(), "period": 2, "subject": "국어", "record_key": "K2",
                 "lesson": "2차시", "title": "둘째 수업", "memos": [{"kind": "step", "idx": 1}]}
        path = app.session_path(day.isoformat(), 2, "국어", "K2")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")

        lessons = app.state(day)["lessons"]

        self.assertEqual(lessons[1]["saved"]["record_key"], "K2")
        self.assertEqual(lessons[1]["saved"]["memos"][0]["idx"], 1)


class SaveFlowTest(FlowTestBase):
    def test_saves_new_flow_by_record_key(self):
        res = app.save_flow(body())
        self.assertEqual(res["status"], "success")
        saved = json.loads((self.flows / "K1.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["goal"], "분수를 더한다")
        self.assertEqual(saved["materials"], ["분수 막대", "딱지"])
        self.assertEqual([s["name"] for s in saved["steps"]], ["도입", "정리"])
        saved_step = saved["steps"][1]
        self.assertEqual({key: saved_step[key] for key in ("name", "minutes", "do", "say", "tip")},
                         {"name": "정리", "minutes": 5, "do": "", "say": "", "tip": ""})
        self.assertEqual(saved_step["teacher_actions"], [])
        self.assertEqual(saved_step["teacher_prompts"], [])
        self.assertEqual(saved_step["student_actions"], [])
        self.assertEqual(saved_step["expected_responses"], [])
        self.assertEqual(saved["publisher"], "아이스크림")
        self.assertEqual(saved["edited"]["by"], "teacher")

    def test_saved_flow_is_found_by_find_flow(self):
        app.save_flow(body())
        found = app.find_flow({"record_key": "K1", "subject": "수학", "title": "분수의 덧셈"})
        self.assertEqual(found["title"], "분수의 덧셈")

    def test_edit_removes_auto_mark_and_keeps_other_fields(self):
        auto = {"record_key": "K1", "subject": "수학", "title": "분수의 덧셈", "publisher": "미래엔",
                "source": "지도서 p.1", "homework": "익힘 1쪽", "auto": {"by": "gemini", "at": "2026-11-22 10:00"},
                "steps": [{"name": "옛 단계", "minutes": 40}]}
        (self.flows / "K1.json").write_text(json.dumps(auto, ensure_ascii=False), encoding="utf-8")
        app.save_flow(body())
        saved = json.loads((self.flows / "K1.json").read_text(encoding="utf-8"))
        self.assertNotIn("auto", saved)  # prepare_lessons 는 auto 가 없으면 '직접 고친 흐름'으로 보고 --redo 로도 안 덮어쓴다
        self.assertEqual(saved["source"], "지도서 p.1")
        self.assertEqual(saved["homework"], "익힘 1쪽")
        self.assertEqual(saved["publisher"], "미래엔")
        self.assertEqual([s["name"] for s in saved["steps"]], ["도입", "정리"])

    def test_saves_into_existing_title_file_when_no_record_key_file(self):
        path = self.flows / "수학__분수의_덧셈.json"
        path.write_text(json.dumps({"subject": "수학", "title": "분수의 덧셈", "steps": []}, ensure_ascii=False), encoding="utf-8")
        app.save_flow(body(record_key=""))
        self.assertTrue(path.is_file())
        self.assertFalse((self.flows / "K1.json").exists())
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["steps"][0]["name"], "도입")

    def test_title_only_lesson_uses_subject_title_file(self):
        app.save_flow(body(record_key=""))
        self.assertTrue((self.flows / "수학__분수의_덧셈.json").is_file())

    def test_materials_accept_list_and_drop_blanks(self):
        b = body()
        b["flow"]["materials"] = ["자", " ", "  가위 "]
        app.save_flow(b)
        self.assertEqual(json.loads((self.flows / "K1.json").read_text(encoding="utf-8"))["materials"], ["자", "가위"])

    def test_control_characters_are_removed_but_newline_kept(self):
        b = body()
        b["flow"]["steps"][0]["do"] = "첫 줄\n둘째 줄\x00\x07끝"
        app.save_flow(b)
        saved = json.loads((self.flows / "K1.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["steps"][0]["do"], "첫 줄\n둘째 줄  끝")

    def test_long_text_is_cut(self):
        b = body()
        b["flow"]["steps"][0]["do"] = "가" * 5000
        app.save_flow(b)
        self.assertEqual(len(json.loads((self.flows / "K1.json").read_text(encoding="utf-8"))["steps"][0]["do"]), 1000)

    def test_flag_keep_cut_saved_and_other_values_dropped(self):
        b = body(); b["flow"]["steps"][0]["flag"] = "keep"; b["flow"]["steps"][1]["flag"] = "아무거나"
        app.save_flow(b)
        steps = json.loads((self.flows / "K1.json").read_text(encoding="utf-8"))["steps"]
        self.assertEqual(steps[0]["flag"], "keep")
        self.assertNotIn("flag", steps[1])  # 옛 흐름과 같은 모양 유지

    def test_cut_flag_roundtrip(self):
        b = body(); b["flow"]["steps"][1]["flag"] = "cut"
        app.save_flow(b)
        self.assertEqual(app.find_flow({"record_key": "K1", "subject": "수학", "title": "x"})["steps"][1]["flag"], "cut")

    def test_odd_record_key_stays_inside_flows_folder(self):
        app.save_flow(body(record_key="../../evil"))
        self.assertEqual([p.parent for p in self.flows.rglob("*.json")], [self.flows])
        self.assertFalse((self.flows.parent / "evil.json").exists())


class PrepareFlagTest(unittest.TestCase):
    def test_parse_flow_keeps_valid_flag_only(self):
        import prepare_lessons as pl
        raw = json.dumps({"goal": "g", "steps": [{"name": "a", "minutes": 20, "flag": "Cut"}, {"name": "b", "minutes": 20, "flag": "??"}, {"name": "c", "minutes": 0}]})
        steps = pl.parse_flow(raw)["steps"]
        self.assertEqual(steps[0]["flag"], "cut")
        self.assertNotIn("flag", steps[1])
        self.assertNotIn("flag", steps[2])


class ValidationTest(FlowTestBase):
    def assertRejected(self, payload, text):
        with self.assertRaises(ValueError) as ctx:
            app.save_flow(payload)
        self.assertIn(text, str(ctx.exception))
        self.assertEqual(list(self.flows.iterdir()), [], "거절한 요청은 파일을 만들면 안 돼요")

    def test_needs_subject_and_lesson(self):
        self.assertRejected(body(subject=""), "과목과 차시")
        self.assertRejected(body(record_key="", title=""), "과목과 차시")

    def test_needs_flow_dict(self):
        self.assertRejected(body(flow="x"), "수업 흐름")
        self.assertRejected(body(flow=None), "수업 흐름")

    def test_step_count_limits(self):
        b = body(); b["flow"]["steps"] = []
        self.assertRejected(b, "1~12개")
        b["flow"]["steps"] = [dict(STEP) for _ in range(13)]
        self.assertRejected(b, "1~12개")
        b["flow"]["steps"] = "도입"
        self.assertRejected(b, "1~12개")

    def test_twelve_steps_ok(self):
        b = body(); b["flow"]["steps"] = [dict(STEP, minutes=3) for _ in range(12)]
        self.assertEqual(app.save_flow(b)["status"], "success")

    def test_step_name_required(self):
        b = body(); b["flow"]["steps"][1]["name"] = "  "
        self.assertRejected(b, "2번째 단계 이름")

    def test_minutes_must_be_number_in_range(self):
        for bad, text in (("abc", "숫자가 아니에요"), (-1, "0~120"), (121, "0~120")):
            b = body(); b["flow"]["steps"][0]["minutes"] = bad
            self.assertRejected(b, text)

    def test_step_must_be_object(self):
        b = body(); b["flow"]["steps"][0] = "도입"
        self.assertRejected(b, "1번째 단계 형식")

    def test_materials_must_be_text_or_list(self):
        b = body(); b["flow"]["materials"] = {"a": 1}
        self.assertRejected(b, "준비물 형식")

    def test_minutes_blank_means_zero(self):
        b = body(); b["flow"]["steps"][0]["minutes"] = ""
        app.save_flow(b)
        self.assertEqual(json.loads((self.flows / "K1.json").read_text(encoding="utf-8"))["steps"][0]["minutes"], 0)


class HttpTest(FlowTestBase):
    def setUp(self):
        super().setUp()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        super().tearDown()

    def post(self, payload, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=10)
        conn.request("POST", "/api/flow", json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                     {"Content-Type": "application/json", **(headers or {})})
        res = conn.getresponse()
        return res.status, json.loads(res.read().decode("utf-8"))

    def test_post_saves(self):
        status, data = self.post(body())
        self.assertEqual((status, data["status"]), (200, "success"))
        self.assertEqual(data["flow"]["steps"][0]["name"], "도입")
        self.assertTrue((self.flows / "K1.json").is_file())

    def test_post_error_is_400_with_korean_message(self):
        b = body(); b["flow"]["steps"][0]["name"] = ""
        status, data = self.post(b)
        self.assertEqual(status, 400)
        self.assertIn("이름이 비어", data["message"])

    def test_other_site_origin_is_refused(self):
        status, _ = self.post(body(), {"Origin": "https://evil.example"})
        self.assertEqual(status, 403)
        self.assertEqual(list(self.flows.iterdir()), [])




class FakeUser32:
    """Windows 창 API 흉내: 호출 순서만 기록한다."""
    def __init__(self, iconic=False):
        self.calls, self._iconic = [], iconic

    def IsIconic(self, hwnd): self.calls.append(("IsIconic", hwnd)); return self._iconic
    def ShowWindow(self, hwnd, cmd): self.calls.append(("ShowWindow", hwnd, cmd))
    def SetWindowPos(self, hwnd, after, *rest): self.calls.append(("SetWindowPos", hwnd, after))
    def keybd_event(self, vk, scan, flags, extra): self.calls.append(("keybd_event", vk, flags))
    def SetForegroundWindow(self, hwnd): self.calls.append(("SetForegroundWindow", hwnd))


class WaitForNewWindowTest(unittest.TestCase):
    def test_returns_new_window_after_a_few_polls(self):
        seen = iter([{1, 2}, {1, 2}, {1, 2, 7}])
        sleeps = []
        got = app.wait_for_new_window(lambda: next(seen), {1, 2}, timeout=5, interval=0.2, sleep=sleeps.append, clock=lambda: 0)
        self.assertEqual(got, 7)
        self.assertEqual(sleeps, [0.2, 0.2])

    def test_gives_up_after_timeout(self):
        t = [0.0]
        def clock(): return t[0]
        def sleep(sec): t[0] += sec
        got = app.wait_for_new_window(lambda: {1, 2}, {1, 2}, timeout=1.0, interval=0.25, sleep=sleep, clock=clock)
        self.assertIsNone(got)
        self.assertGreaterEqual(t[0], 1.0)

    def test_picks_last_when_several_new(self):
        self.assertEqual(app.wait_for_new_window(lambda: {1, 5, 9}, {1}, sleep=lambda s: None, clock=lambda: 0), 9)


class RaiseWindowTest(unittest.TestCase):
    def test_order_normal_window(self):
        u = FakeUser32()
        app.raise_window(u, 42)
        names = [c[0] for c in u.calls]
        self.assertEqual(names, ["IsIconic", "SetWindowPos", "SetWindowPos", "keybd_event", "keybd_event", "SetForegroundWindow"])
        self.assertEqual([c[2] for c in u.calls if c[0] == "SetWindowPos"], [-1, -2])    # 항상 위 → 해제
        self.assertEqual([c[2] for c in u.calls if c[0] == "keybd_event"], [0, 2])       # 누름 → 뗌
        self.assertEqual(u.calls[-1], ("SetForegroundWindow", 42))

    def test_restores_minimized_window_first(self):
        u = FakeUser32(iconic=True)
        app.raise_window(u, 42)
        self.assertEqual(u.calls[1], ("ShowWindow", 42, 9))


class OpenWindowTest(unittest.TestCase):
    """open_window 가 새 창을 앞으로 올리는 일을 시작하되, 실패해도 창 열기는 그대로 성공해야 한다."""
    def setUp(self):
        self._saved = (app.chrome_path, app.screen_size, app.subprocess.Popen, app._is_windows, app.chrome_windows, app._win_api, app._raise_new_window)
        self.popen_calls, self.raised = [], threading.Event()
        app.chrome_path = lambda: "chrome.exe"
        app.screen_size = lambda: (1920, 1080)
        app.subprocess.Popen = lambda args, **kw: self.popen_calls.append(args)
        app._win_api = lambda: object()
        app._raise_new_window = lambda before, *_args: (setattr(self, "before", before), self.raised.set())

    def tearDown(self):
        (app.chrome_path, app.screen_size, app.subprocess.Popen, app._is_windows, app.chrome_windows, app._win_api, app._raise_new_window) = self._saved

    def test_windows_remembers_old_windows_and_raises_new_one(self):
        app._is_windows = lambda: True
        app.chrome_windows = lambda api: {11, 12}
        self.assertEqual(app.open_window("https://x.example/", "right", {}), "창을 열었어요.")
        self.assertEqual(len(self.popen_calls), 1)
        self.assertTrue(self.raised.wait(2))
        self.assertEqual(self.before, {11, 12})

    def test_not_windows_does_not_try(self):
        app._is_windows = lambda: False
        self.assertEqual(app.open_window("https://x.example/", "right", {}), "창을 열었어요.")
        self.assertFalse(self.raised.wait(0.3))

    def test_window_listing_failure_does_not_block_opening(self):
        app._is_windows = lambda: True
        def boom(api): raise OSError("user32 없음")
        app.chrome_windows = boom
        self.assertEqual(app.open_window("https://x.example/", "right", {}), "창을 열었어요.")
        self.assertEqual(len(self.popen_calls), 1)
        self.assertFalse(self.raised.wait(0.3))


class FaviconTest(unittest.TestCase):
    def test_favicon_path_returns_small_svg_icon(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=2)
        self.addCleanup(conn.close)

        conn.request("GET", "/favicon.ico")
        response = conn.getresponse()
        icon = response.read().decode("utf-8")

        self.assertEqual(response.status, 200)
        self.assertIn("image/svg+xml", response.getheader("Content-Type"))
        self.assertIn("<svg", icon)
        self.assertIn("</svg>", icon)

    def test_mobile_stylesheet_is_served(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=2)
        self.addCleanup(conn.close)

        conn.request("GET", "/mobile.css")
        response = conn.getresponse()
        css = response.read().decode("utf-8")

        self.assertEqual(response.status, 200)
        self.assertIn("text/css", response.getheader("Content-Type"))
        self.assertIn("@media (max-width: 720px)", css)


if __name__ == "__main__":
    unittest.main()
