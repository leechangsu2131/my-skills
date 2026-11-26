"""assistant_server.save_audio 시험(ISSUE-010: 녹음 조각 순번 확인·재전송). 표준 라이브러리만 쓴다.

    python -m unittest discover -s tests -v      (skills/teacherlesson-assistant 폴더에서)

임시 폴더만 쓰므로 내 문서의 실제 녹음은 건드리지 않는다.
"""
import http.client
import json
import pathlib
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import assistant_server as app  # noqa: E402

DAY = "2026-11-26"


def q(seq, name="3교시_수학_100000", ext="webm", day=DAY):
    return {"date": [day], "name": [name], "seq": [str(seq)], "ext": [ext]}


class SaveAudioTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.sessions = pathlib.Path(self._tmp.name) / "sessions"
        self._saved = app.SESSIONS
        app.SESSIONS = self.sessions
        app._REC_STATE.clear()
        self.file = self.sessions / DAY / "3교시_수학_100000.webm"

    def tearDown(self):
        app.SESSIONS = self._saved
        app._REC_STATE.clear()
        self._tmp.cleanup()

    # ── 정상 흐름 ──
    def test_chunks_in_order_are_appended(self):
        r0 = app.save_audio(q(0), b"AAA")
        r1 = app.save_audio(q(1), b"BB")
        r2 = app.save_audio(q(2), b"C")
        self.assertEqual(self.file.read_bytes(), b"AAABBC")
        self.assertEqual([r0["status"], r1["status"], r2["status"]], ["success"] * 3)
        self.assertEqual((r0["bytes"], r1["bytes"], r2["bytes"]), (3, 5, 6))
        self.assertEqual(r2["next"], 3)
        self.assertNotIn("duplicate", r2)

    # ── 순번이 건너뜀 ──
    def test_gap_is_rejected_and_nothing_is_written(self):
        app.save_audio(q(0), b"AAA")
        res = app.save_audio(q(2), b"CC")
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["code"], "gap")
        self.assertEqual(res["expected"], 1)
        self.assertEqual(res["got"], 2)
        self.assertEqual(self.file.read_bytes(), b"AAA")

    def test_gap_then_resend_from_expected_gives_a_whole_file(self):
        app.save_audio(q(0), b"AAA")
        self.assertEqual(app.save_audio(q(2), b"CC")["code"], "gap")
        app.save_audio(q(1), b"BB")      # 클라이언트가 빠진 조각부터 다시 보냄
        app.save_audio(q(2), b"CC")
        self.assertEqual(self.file.read_bytes(), b"AAABBCC")

    def test_chunk_without_first_chunk_is_rejected_and_creates_no_file(self):
        res = app.save_audio(q(1), b"BB")
        self.assertEqual((res["code"], res["expected"]), ("gap", 0))
        self.assertFalse(self.file.exists())

    # ── 재전송(응답을 못 받음) ──
    def test_resend_of_same_chunk_is_ok_and_not_appended_twice(self):
        app.save_audio(q(0), b"AAA")
        app.save_audio(q(1), b"BB")
        again = app.save_audio(q(1), b"BB")
        self.assertEqual(again["status"], "success")
        self.assertTrue(again["duplicate"])
        self.assertEqual(again["next"], 2)
        self.assertEqual(self.file.read_bytes(), b"AAABB")

    def test_resend_of_first_chunk_is_ok_not_a_name_clash(self):
        app.save_audio(q(0), b"AAA")
        again = app.save_audio(q(0), b"AAA")
        self.assertTrue(again["duplicate"])
        self.assertEqual(self.file.read_bytes(), b"AAA")

    def test_same_seq_with_different_content_is_an_error_not_overwritten(self):
        app.save_audio(q(0), b"AAA")
        app.save_audio(q(1), b"BB")
        with self.assertRaises(ValueError):
            app.save_audio(q(1), b"XX")
        self.assertEqual(self.file.read_bytes(), b"AAABB")

    # ── 같은 이름의 새 녹음(기존 동작 유지) ──
    def test_new_recording_with_same_name_is_still_refused_with_new_name_hint(self):
        app.save_audio(q(0), b"AAA")
        with self.assertRaises(ValueError) as cm:
            app.save_audio(q(0), b"ZZZ")        # 내용이 다른 첫 조각 = 같은 이름의 새 녹음
        self.assertIn("3교시_수학_100000_2", str(cm.exception))
        self.assertEqual(self.file.read_bytes(), b"AAA")

    def test_existing_file_from_before_server_start_is_not_overwritten(self):
        self.file.parent.mkdir(parents=True)
        self.file.write_bytes(b"OLD")
        with self.assertRaises(ValueError):
            app.save_audio(q(0), b"NEW")
        self.assertEqual(self.file.read_bytes(), b"OLD")

    # ── 서버를 다시 켠 뒤 ──
    def test_after_server_restart_next_chunk_is_appended_to_existing_file(self):
        app.save_audio(q(0), b"AAA")
        app.save_audio(q(1), b"BB")
        app._REC_STATE.clear()                   # 서버를 껐다 켠 것과 같음
        res = app.save_audio(q(2), b"C")
        self.assertEqual(res["status"], "success")
        self.assertEqual(self.file.read_bytes(), b"AAABBC")
        self.assertEqual(app.save_audio(q(1), b"BB")["duplicate"], True)   # 이미 있던 순번 재전송은 쓰지 않음
        self.assertEqual(self.file.read_bytes(), b"AAABBC")

    # ── 쓰다 실패 ──
    def test_failed_write_is_rolled_back_so_the_resend_is_clean(self):
        app.save_audio(q(0), b"AAA")
        real_open = open

        def half_then_fail(path, mode="r", *a, **k):
            fh = real_open(path, mode, *a, **k)
            if str(path) == str(self.file) and mode == "ab":
                real_write = fh.write

                def write(data):
                    real_write(data[:1])         # 반만 쓰고
                    fh.flush()
                    raise OSError("disk full")   # 실패
                fh.write = write
            return fh

        with mock.patch("builtins.open", half_then_fail):
            with self.assertRaises(OSError):
                app.save_audio(q(1), b"BB")
        self.assertEqual(self.file.read_bytes(), b"AAA")      # 반쯤 쓴 조각이 남지 않음
        app.save_audio(q(1), b"BB")                           # 순번도 그대로라 그대로 다시 보낼 수 있음
        self.assertEqual(self.file.read_bytes(), b"AAABB")

    def test_failed_first_chunk_leaves_no_file(self):
        real_open = open

        def fail(path, mode="r", *a, **k):
            if str(path) == str(self.file) and mode == "wb":
                raise OSError("disk full")
            return real_open(path, mode, *a, **k)

        with mock.patch("builtins.open", fail):
            with self.assertRaises(OSError):
                app.save_audio(q(0), b"AAA")
        self.assertFalse(self.file.exists())
        app.save_audio(q(0), b"AAA")
        self.assertEqual(self.file.read_bytes(), b"AAA")

    # ── 입력 검사 ──
    def test_bad_seq_and_date_are_errors(self):
        with self.assertRaises(ValueError):
            app.save_audio(q(-1), b"A")
        with self.assertRaises(ValueError):
            app.save_audio(q(0, day="2026-13-40"), b"A")

    def test_mp4_and_webm_with_same_name_are_separate_files(self):
        app.save_audio(q(0, ext="webm"), b"W")
        app.save_audio(q(0, ext="mp4"), b"M")
        self.assertEqual((self.sessions / DAY / "3교시_수학_100000.mp4").read_bytes(), b"M")
        self.assertEqual(self.file.read_bytes(), b"W")


class RecEndpointTest(unittest.TestCase):
    """POST /api/rec — 순번 빠짐은 409 와 필요한 순번을, 정상은 200 을 돌려준다."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._saved = app.SESSIONS
        app.SESSIONS = pathlib.Path(self._tmp.name) / "sessions"
        app._REC_STATE.clear()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        app.SESSIONS = self._saved
        app._REC_STATE.clear()
        self._tmp.cleanup()

    def post(self, seq, data):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        path = f"/api/rec?date={DAY}&name=rec1&seq={seq}&ext=webm"
        conn.request("POST", path, body=data, headers={"Content-Length": str(len(data))})
        resp = conn.getresponse()
        out = (resp.status, json.loads(resp.read().decode("utf-8")))
        conn.close()
        return out

    def test_http_flow_ok_gap_resend(self):
        status, j = self.post(0, b"AAA")
        self.assertEqual((status, j["status"]), (200, "success"))
        status, j = self.post(2, b"CC")
        self.assertEqual((status, j["code"], j["expected"]), (409, "gap", 1))
        status, j = self.post(1, b"BB")
        self.assertEqual((status, j["status"]), (200, "success"))
        status, j = self.post(1, b"BB")
        self.assertEqual((status, j.get("duplicate")), (200, True))
        status, j = self.post(2, b"CC")
        self.assertEqual((status, j["bytes"]), (200, 7))


if __name__ == "__main__":
    unittest.main()
