"""day_recorder.py 시험 (T117) — 진짜 마이크·ffmpeg 없이 가짜 문자열·가짜 프로세스로."""
import json
import pathlib
import sys
import tempfile
import unittest
from datetime import date, datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import day_recorder as dr  # noqa: E402

NEW_FMT = '''[dshow @ 000001] DirectShow video devices (some may be both video and audio devices)
[dshow @ 000001]  "Integrated Camera" (video)
[dshow @ 000001]     Alternative name "@device_pnp_\\\\?\\usb#vid_0c45"
[dshow @ 000001] DirectShow audio devices
[dshow @ 000001]  "마이크 배열 (Realtek(R) Audio)" (audio)
[dshow @ 000001]     Alternative name "@device_cm_{33D9A762}\\wave_{AAAA}"
[dshow @ 000001]  "USB 마이크 (Blue)" (audio)
[dshow @ 000001]     Alternative name "@device_cm_{33D9A762}\\wave_{BBBB}"
dummy: Immediate exit requested
'''
OLD_FMT = '''[dshow @ 0] DirectShow video devices
[dshow @ 0]  "Cam"
[dshow @ 0]  "Alternative name" is skipped
[dshow @ 0] DirectShow audio devices
[dshow @ 0]  "Microphone (Realtek)"
[dshow @ 0]  "Line In"
'''


class PureTests(unittest.TestCase):
    def test_parse_new_format_audio_only(self):
        self.assertEqual(dr.parse_dshow_audio_devices(NEW_FMT), ["마이크 배열 (Realtek(R) Audio)", "USB 마이크 (Blue)"])

    def test_parse_old_format_uses_section(self):
        self.assertEqual(dr.parse_dshow_audio_devices(OLD_FMT), ["Microphone (Realtek)", "Line In"])

    def test_parse_empty_and_dupes(self):
        self.assertEqual(dr.parse_dshow_audio_devices(""), [])
        self.assertEqual(dr.parse_dshow_audio_devices(None), [])
        self.assertEqual(dr.parse_dshow_audio_devices('"A" (audio)\n"A" (audio)'), ["A"])

    def test_pick_microphone(self):
        devs = ["마이크 배열 (Realtek)", "USB 마이크 (Blue)"]
        self.assertEqual(dr.pick_microphone(devs, ""), devs[0])
        self.assertEqual(dr.pick_microphone(devs, "blue"), devs[1])
        self.assertIsNone(dr.pick_microphone(devs, "없는마이크"))      # 엉뚱한 마이크로 몰래 녹음하지 않음
        self.assertIsNone(dr.pick_microphone([], ""))

    def test_segment_name_roundtrip(self):
        m = datetime(2026, 11, 30, 9, 5, 7)
        self.assertEqual(dr.segment_name(m), "090507.mp3")
        self.assertEqual(dr.parse_segment_start("090507.mp3", date(2026, 11, 30)), m)
        self.assertEqual(dr.parse_segment_start("/x/y/090507.mp3", date(2026, 11, 30)), m)

    def test_parse_segment_rejects_bad_names(self):
        d = date(2026, 11, 30)
        for bad in ["recorder.log", "9507.mp3", "250000.mp3", "126000.mp3", "120061.mp3", "120000", "abc123.mp3"]:
            self.assertIsNone(dr.parse_segment_start(bad, d), bad)

    def test_seconds_until_midnight(self):
        self.assertEqual(dr.seconds_until_midnight(datetime(2026, 11, 30, 23, 59, 0)), 60)
        self.assertEqual(dr.seconds_until_midnight(datetime(2026, 11, 30, 0, 0, 0)), 86400)
        self.assertEqual(dr.seconds_until_midnight(datetime(2026, 11, 30, 23, 59, 59, 500000)), 1)

    def test_build_record_command(self):
        cmd = dr.build_record_command("ffmpeg", "USB 마이크", pathlib.Path("/d/2026-11-30"), 3600)
        self.assertEqual(cmd[0], "ffmpeg")
        self.assertIn("audio=USB 마이크", cmd)
        self.assertEqual(cmd[cmd.index("-t") + 1], "3600")
        self.assertEqual(cmd[cmd.index("-segment_time") + 1], "1800")
        self.assertEqual(cmd[cmd.index("-b:a") + 1], "64k")
        self.assertEqual(cmd[cmd.index("-ac") + 1], "1")
        self.assertEqual(cmd[cmd.index("-strftime") + 1], "1")
        self.assertTrue(cmd[-1].endswith("%H%M%S.mp3"))
        self.assertIn("2026-11-30", cmd[-1])

    def test_may_restart(self):
        self.assertTrue(dr.may_restart([], 1000))
        self.assertTrue(dr.may_restart([100, 200, 300, 400], 450))
        self.assertFalse(dr.may_restart([100, 200, 300, 400, 410], 450))
        self.assertTrue(dr.may_restart([100, 200, 300, 400, 410], 1500))   # 10분이 지나면 다시 센다

    def test_summarize_day(self):
        d = date(2026, 11, 30)
        s = dr.summarize_day([("091500.mp3", 100), ("084500.mp3", 50), ("recorder.log", 999)], d)
        self.assertEqual(s, {"count": 2, "bytes": 150, "first": "08:45:00", "last": "09:15:00"})
        self.assertEqual(dr.summarize_day([], d), {"count": 0, "bytes": 0, "first": None, "last": None})


class FakeProc:
    def __init__(self, pid=4242, codes=None, on_poll=None):
        self.pid = pid
        self._codes = list(codes or [])
        self.on_poll = on_poll
        self.stdin = FakeStdin()
        self.killed = False

    def poll(self):
        if self.on_poll:
            self.on_poll(self)
        return self._codes.pop(0) if self._codes else None

    def kill(self):
        self.killed = True
        self._codes = [-9]


class FakeStdin:
    def __init__(self): self.data = b""
    def write(self, b): self.data += b
    def flush(self): pass


class Clock:
    def __init__(self, t): self.t = t; self.mono = 0.0
    def now(self): return self.t
    def sleep(self, s): self.mono += s
    def monotonic(self): return self.mono


class RecorderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.clock = Clock(datetime(2026, 11, 30, 8, 30, 0))

    def rec(self, popen=None, alive=lambda pid: False, cfg=None):
        return dr.Recorder(root=self.tmp, cfg=cfg or {}, popen=popen or (lambda *a, **k: FakeProc()),
                           now=self.clock.now, sleep=self.clock.sleep, monotonic=self.clock.monotonic, alive=alive)

    def patch_ffmpeg(self, found="/bin/ffmpeg", devices=("USB 마이크",)):
        self._f = dr.audio_export.find_ffmpeg, dr.list_devices
        dr.audio_export.find_ffmpeg = lambda cfg, **k: found
        dr.list_devices = lambda ffmpeg, runner=None: list(devices)
        self.addCleanup(lambda: (setattr(dr.audio_export, "find_ffmpeg", self._f[0]), setattr(dr, "list_devices", self._f[1])))

    # ── start ──
    def test_start_spawns_and_writes_pid(self):
        self.patch_ffmpeg()
        calls = []
        r = self.rec(popen=lambda cmd, **kw: (calls.append((cmd, kw)), FakeProc(pid=777))[1])
        msg = r.start()
        self.assertIn("시작했어요", msg)
        self.assertEqual(json.loads(r.pid_file.read_text(encoding="utf-8"))["pid"], 777)
        cmd, kw = calls[0]
        self.assertEqual(cmd[-3:], ["run", "--mic", "USB 마이크"])
        self.assertTrue(r.log_file.exists())

    def test_start_twice_is_refused(self):
        self.patch_ffmpeg()
        calls = []
        r = self.rec(popen=lambda cmd, **kw: (calls.append(1), FakeProc(pid=5))[1], alive=lambda pid: pid == 5)
        r.start()
        self.assertIn("이미 녹음 중", r.start())
        self.assertEqual(len(calls), 1)                         # 두 번 켜지지 않음

    def test_stale_pid_file_is_cleaned_and_restart_allowed(self):
        self.patch_ffmpeg()
        r = self.rec(alive=lambda pid: False)
        r.root.mkdir(parents=True, exist_ok=True)
        r.pid_file.write_text(json.dumps({"pid": 99}), encoding="utf-8")
        self.assertFalse(r.is_running())
        self.assertFalse(r.pid_file.exists())
        self.assertIn("시작했어요", r.start())

    def test_start_without_ffmpeg_gives_install_help(self):
        self.patch_ffmpeg(found=None)
        self.assertIn("ffmpeg", self.rec().start())

    def test_start_without_mic_or_wrong_mic(self):
        self.patch_ffmpeg(devices=())
        self.assertIn("마이크를 찾지 못했어요", self.rec().start())
        self.patch_ffmpeg(devices=("A 마이크", "B 마이크"))
        msg = self.rec(cfg={"day_recorder_mic": "없는것"}).start()
        self.assertIn("'없는것' 이름의 마이크가 없어요", msg)
        self.assertIn("A 마이크", msg)

    def test_config_mic_is_used(self):
        self.patch_ffmpeg(devices=("A 마이크", "B 마이크"))
        calls = []
        r = self.rec(popen=lambda cmd, **kw: (calls.append(cmd), FakeProc())[1], cfg={"day_recorder_mic": "b"})
        r.start()
        self.assertEqual(calls[0][-1], "B 마이크")

    # ── stop ──
    def test_stop_when_not_running(self):
        self.assertEqual(self.rec().stop(), "켜져 있지 않아요.")

    def test_stop_graceful(self):
        state = {"alive": True}
        r = self.rec(alive=lambda pid: state["alive"])
        r.root.mkdir(parents=True, exist_ok=True)
        r.pid_file.write_text(json.dumps({"pid": 9}), encoding="utf-8")
        orig_sleep = r.sleep
        def sleeper(s):                                         # 끄기 신호를 본 프로그램이 끝난 것처럼
            if r.stop_flag.exists():
                state["alive"] = False
            orig_sleep(s)
        r.sleep = sleeper
        self.assertEqual(r.stop(), "녹음을 껐어요.")
        self.assertFalse(r.pid_file.exists())

    def test_stop_forces_when_no_answer(self):
        r = self.rec(alive=lambda pid: True)
        killed = []
        r._kill = killed.append
        r.root.mkdir(parents=True, exist_ok=True)
        r.pid_file.write_text(json.dumps({"pid": 9}), encoding="utf-8")
        self.assertIn("강제로", r.stop(wait_seconds=2))
        self.assertEqual(killed, [9])
        self.assertFalse(r.pid_file.exists())

    # ── run ──
    def run_with(self, procs, patch=True, devices=("USB 마이크",)):
        if patch:
            self.patch_ffmpeg(devices=devices)
        seq = list(procs)
        launched = []
        def popen(cmd, **kw):
            launched.append(cmd)
            return seq.pop(0)
        r = self.rec(popen=popen)
        return r, launched

    def test_run_restarts_after_crash_then_stops_on_flag(self):
        flag_holder = {}
        crash = FakeProc(codes=[1])                               # 바로 죽음
        good = FakeProc(on_poll=lambda p: flag_holder["r"].stop_flag.write_text("x", encoding="utf-8"))
        r, launched = self.run_with([crash, good])
        flag_holder["r"] = r
        self.assertEqual(r.run("USB"), 0)
        self.assertEqual(len(launched), 2)                        # 한 번 다시 켬
        self.assertEqual(good.stdin.data, b"q")                   # 깔끔히 닫으라고 q 를 보냄
        self.assertIn("끄기 요청을 받아 끝냄", r.log_file.read_text(encoding="utf-8"))
        self.assertTrue((self.tmp / "2026-11-30").is_dir())

    def test_run_gives_up_after_too_many_crashes(self):
        r, launched = self.run_with([FakeProc(codes=[1]) for _ in range(dr.MAX_RESTARTS + 1)])
        self.assertEqual(r.run("USB"), 1)
        self.assertEqual(len(launched), dr.MAX_RESTARTS + 1)
        self.assertIn("확인해 주세요", r.log_file.read_text(encoding="utf-8"))

    def test_run_moves_to_next_day_folder_at_midnight(self):
        flag_holder = {}
        def end_at_midnight(p):                                   # 첫 ffmpeg 는 자정에 정상 종료
            self.clock.t = datetime(2026, 12, 1, 0, 0, 1)
        first = FakeProc(codes=[0], on_poll=end_at_midnight)
        second = FakeProc(on_poll=lambda p: flag_holder["r"].stop_flag.write_text("x", encoding="utf-8"))
        self.clock.t = datetime(2026, 11, 30, 23, 59, 50)
        r, launched = self.run_with([first, second])
        flag_holder["r"] = r
        self.assertEqual(r.run("USB"), 0)
        self.assertEqual(len(launched), 2)
        self.assertIn("2026-11-30", launched[0][-1])
        self.assertIn("2026-12-01", launched[1][-1])             # 새 날짜 폴더
        self.assertEqual(launched[0][launched[0].index("-t") + 1], "10")
        self.assertNotIn("끊김", r.log_file.read_text(encoding="utf-8"))
        self.assertNotIn("ffmpeg 가 끝남", r.log_file.read_text(encoding="utf-8"))   # 자정 교체는 '끊김'으로 세지 않음

    def test_run_without_mic_or_ffmpeg_exits(self):
        r, _ = self.run_with([], devices=())
        self.assertEqual(r.run(""), 3)
        r2, _ = self.run_with([], patch=False)
        self.patch_ffmpeg(found=None)
        self.assertEqual(self.rec().run(""), 2)

    def test_stuck_ffmpeg_is_killed_on_stop(self):
        flag_holder = {}
        stuck = FakeProc(on_poll=lambda p: flag_holder["r"].stop_flag.write_text("x", encoding="utf-8"))
        r, _ = self.run_with([stuck])
        flag_holder["r"] = r
        r.run("USB")
        self.assertTrue(stuck.killed)

    # ── status ──
    def test_status(self):
        r = self.rec(alive=lambda pid: pid == 31)
        r.root.mkdir(parents=True, exist_ok=True)
        r.pid_file.write_text(json.dumps({"pid": 31, "mic": "USB 마이크"}), encoding="utf-8")
        d = self.tmp / "2026-11-30"
        d.mkdir()
        (d / "083000.mp3").write_bytes(b"x" * 10)
        (d / "090000.mp3").write_bytes(b"x" * 20)
        s = r.status()
        self.assertTrue(s["running"])
        self.assertEqual((s["pid"], s["mic"]), (31, "USB 마이크"))
        self.assertEqual(s["today"], {"count": 2, "bytes": 30, "first": "08:30:00", "last": "09:00:00"})

    def test_status_when_nothing(self):
        s = self.rec().status()
        self.assertFalse(s["running"])
        self.assertEqual(s["today"]["count"], 0)


if __name__ == "__main__":
    unittest.main()
