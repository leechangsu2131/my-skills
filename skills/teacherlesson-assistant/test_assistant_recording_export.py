"""assistant_server.py 의 녹음 재생(/api/recording/…)과 클로바노트용 내보내기(/api/recording-export/…) 시험 (T99).

    python -m unittest test_assistant_recording_export -v      (이 폴더에서)

임시 폴더의 가짜 녹음만 쓴다. 변환기는 가짜로 바꾸고, 진짜 ffmpeg 가 있으면 끝에서 끝까지 도는 시험이 하나 더 돈다.
"""
import http.client
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.parse
from http.server import ThreadingHTTPServer
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import assistant_server as app  # noqa: E402

DAY = "2026-11-27"
NAME = "3교시_국어_101500.webm"


class RecordingExportTestBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = pathlib.Path(self._tmp.name)
        self._saved = (app.SESSIONS, app.load_config)
        app.SESSIONS = root / "sessions"
        app.load_config = lambda: {}
        (app.SESSIONS / DAY).mkdir(parents=True)
        self.src = app.SESSIONS / DAY / NAME
        self.src.write_bytes(b"WEBM-ORIGINAL")
        self.age(3600)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        app.SESSIONS, app.load_config = self._saved
        self._tmp.cleanup()

    def age(self, seconds):
        stamp = time.time() - seconds
        os.utime(self.src, (stamp, stamp))

    def get(self, path, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=20)
        conn.request("GET", path, headers=headers or {})
        res = conn.getresponse()
        body = res.read()
        conn.close()
        return res, body

    def export(self, day=DAY, name=NAME, query=""):
        return self.get(f"/api/recording-export/{day}/{urllib.parse.quote(name)}{query}")


class RecordingStillWorksTest(RecordingExportTestBase):
    """재생 주소를 검사 함수(recording_file)로 옮긴 뒤에도 예전과 똑같이 동작하는지."""

    def test_playback_serves_the_original_with_its_type(self):
        res, body = self.get(f"/api/recording/{DAY}/{urllib.parse.quote(NAME)}")
        self.assertEqual((res.status, body, res.getheader("Content-Type")), (200, b"WEBM-ORIGINAL", "audio/webm"))

    def test_playback_range_request(self):
        res, body = self.get(f"/api/recording/{DAY}/{urllib.parse.quote(NAME)}", {"Range": "bytes=0-3"})
        self.assertEqual((res.status, body), (206, b"WEBM"))

    def test_playback_errors_keep_their_codes(self):
        quoted = urllib.parse.quote(NAME)
        cases = [
            (f"/api/recording/not-a-date/{quoted}", 400),
            (f"/api/recording/{DAY}/{urllib.parse.quote('없는.webm')}", 404),
            (f"/api/recording/{DAY}/{urllib.parse.quote('a.wav')}", 404),
            (f"/api/recording/{DAY}/..%2F{quoted}", 404),
            (f"/api/recording/{DAY}", 404),
            (f"/api/recording/{DAY}/a/b.webm", 404),
        ]
        for path, code in cases:
            self.assertEqual(self.get(path)[0].status, code, path)


class RecordingExportTest(RecordingExportTestBase):
    def test_success_sends_mp3_with_korean_download_name_and_keeps_the_original(self):
        def fake_convert(src, fmt, ffmpeg, **kw):
            out = pathlib.Path(src).parent / "export" / f"{pathlib.Path(src).stem}.{fmt}"
            out.parent.mkdir(exist_ok=True)
            out.write_bytes(b"MP3-BYTES")
            return out
        with mock.patch.object(app.audio_export, "find_ffmpeg", return_value="ffmpeg"), \
                mock.patch.object(app.audio_export, "convert", side_effect=fake_convert) as conv:
            res, body = self.export()
        self.assertEqual((res.status, body), (200, b"MP3-BYTES"))
        self.assertEqual(res.getheader("Content-Type"), "audio/mpeg")
        self.assertEqual(res.getheader("Content-Length"), str(len(b"MP3-BYTES")))
        disposition = res.getheader("Content-Disposition")
        self.assertIn("attachment", disposition)
        self.assertIn("filename*=UTF-8''" + urllib.parse.quote("3교시_국어_101500.mp3"), disposition)
        self.assertEqual(conv.call_args.args[1], "mp3")
        self.assertEqual(self.src.read_bytes(), b"WEBM-ORIGINAL")        # 원본은 그대로

    def test_format_m4a_is_allowed(self):
        with mock.patch.object(app.audio_export, "find_ffmpeg", return_value="ffmpeg"), \
                mock.patch.object(app.audio_export, "convert") as conv:
            out = self.src.parent / "export" / "x.m4a"
            out.parent.mkdir(exist_ok=True)
            out.write_bytes(b"M4A")
            conv.return_value = out
            res, _ = self.export(query="?format=m4a")
        self.assertEqual((res.status, res.getheader("Content-Type")), (200, "audio/mp4"))

    def test_other_formats_are_rejected_before_anything_runs(self):
        with mock.patch.object(app.audio_export, "convert") as conv:
            res, body = self.export(query="?format=wav")
        self.assertEqual(res.status, 400)
        self.assertIn("mp3", body.decode("utf-8"))
        conv.assert_not_called()

    def test_bad_name_date_and_path_are_rejected(self):
        quoted = urllib.parse.quote(NAME)
        cases = [
            (f"/api/recording-export/not-a-date/{quoted}", 400),
            (f"/api/recording-export/{DAY}/{urllib.parse.quote('없는.webm')}", 404),
            (f"/api/recording-export/{DAY}/{urllib.parse.quote('a.wav')}", 404),
            (f"/api/recording-export/{DAY}/..%2F{quoted}", 404),
            (f"/api/recording-export/{DAY}/..%2F..%2F{quoted}", 404),
            (f"/api/recording-export/{DAY}", 404),
        ]
        with mock.patch.object(app.audio_export, "convert") as conv:
            for path, code in cases:
                self.assertEqual(self.get(path)[0].status, code, path)
        conv.assert_not_called()

    def test_still_recording_file_is_409_and_not_converted(self):
        self.age(2)
        with mock.patch.object(app.audio_export, "convert") as conv:
            res, body = self.export()
        self.assertEqual(res.status, 409)
        self.assertIn("녹음 중", body.decode("utf-8"))
        conv.assert_not_called()

    def test_missing_ffmpeg_is_501_with_install_help(self):
        with mock.patch.object(app.audio_export, "find_ffmpeg", return_value=None):
            res, body = self.export()
        self.assertEqual(res.status, 501)
        self.assertIn("winget install Gyan.FFmpeg", body.decode("utf-8"))
        self.assertFalse((self.src.parent / "export").exists())

    def test_conversion_failure_is_500_with_the_reason(self):
        with mock.patch.object(app.audio_export, "find_ffmpeg", return_value="ffmpeg"), \
                mock.patch.object(app.audio_export, "convert", side_effect=app.audio_export.ExportError("변환에 실패했어요: 깨진 파일")):
            res, body = self.export()
        self.assertEqual(res.status, 500)
        self.assertIn("깨진 파일", body.decode("utf-8"))

    def test_untrusted_host_is_refused_like_every_other_route(self):
        res, _ = self.get(f"/api/recording-export/{DAY}/{urllib.parse.quote(NAME)}", {"Host": "evil.example"})
        self.assertEqual(res.status, 403)

    def test_recording_list_ignores_the_export_folder(self):
        export = self.src.parent / "export"
        export.mkdir()
        (export / "3교시_국어_101500.mp3").write_bytes(b"x")
        files = [item["file"] for item in app.recordings_for_day(DAY)]
        self.assertEqual(files, [NAME])

    @unittest.skipIf(shutil.which("ffmpeg") is None, "ffmpeg 가 PATH 에 없음")
    def test_end_to_end_with_real_ffmpeg(self):
        self.src.unlink()
        made = subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
                               "-c:a", "libopus", str(self.src)], capture_output=True)
        self.assertEqual(made.returncode, 0, made.stderr)
        self.age(3600)
        res, body = self.export()
        self.assertEqual(res.status, 200)
        self.assertTrue(body[:3] == b"ID3" or body[0] == 0xFF)
        self.assertTrue((self.src.parent / "export" / "3교시_국어_101500.mp3").is_file())
        again, body2 = self.export()                     # 두 번째는 저장해 둔 것을 다시 보냄
        self.assertEqual((again.status, body2), (200, body))


if __name__ == "__main__":
    unittest.main()
