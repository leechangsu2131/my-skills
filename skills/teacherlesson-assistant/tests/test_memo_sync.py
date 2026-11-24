"""memo_sync.py 시험. 진짜 Supabase 에는 가지 않는다: urllib.request.urlopen 을 가짜로 바꿔 요청을 기록·응답한다.

    python -m unittest discover -s tests -v      (skills/teacherlesson-assistant 폴더에서)

안전장치: 중앙 .env 를 읽지 않고(load_env 를 막음) 주소·키를 가짜 값으로 바꾼다. 데이터 폴더는 임시 폴더다.
"""
import contextlib
import io
import json
import os
import pathlib
import socket
import sys
import tempfile
import unittest
import urllib.error
from datetime import datetime, timedelta
from unittest import mock
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import memo_sync as ms  # noqa: E402

FAKE_URL = "https://memo-test.invalid"
FAKE_KEY = "test-service-key-not-real"


class FakeResponse:
    def __init__(self, payload):
        self.raw = b"" if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self.raw


class FakeNet:
    """urlopen 대용. handler(rec) 가 응답 내용을 돌려주거나 예외를 던진다."""

    def __init__(self):
        self.requests = []
        self.handler = lambda rec: None

    def __call__(self, req, timeout=None):
        rec = {"method": req.get_method(), "url": req.full_url, "timeout": timeout,
               "headers": {k.lower(): v for k, v in req.header_items()},
               "body": json.loads(req.data.decode("utf-8")) if req.data else None}
        self.requests.append(rec)
        return FakeResponse(self.handler(rec))


def http_error(code):
    return urllib.error.HTTPError(FAKE_URL, code, "x", {}, None)


def session(date="2026-11-25", period=3, subject="수학", memos=None):
    return {"date": date, "period": period, "subject": subject, "publisher": "출판사", "title": "분수의 덧셈",
            "unit": "6. 단원", "lesson": "4", "record_key": "lesson-0001", "notice": "", "memos": memos or []}


def memo(kind, text, at, t="01:00", **extra):
    return {"t": t, "at": at, "kind": kind, "text": text, **extra}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = pathlib.Path(self.tmp.name)
        self.net = FakeNet()
        env = {"SUPABASE_URL": FAKE_URL, "SUPABASE_SERVICE_ROLE_KEY": FAKE_KEY, "MEMO_PC": "시험PC"}
        patches = [
            mock.patch.dict(os.environ, env),
            mock.patch.object(ms, "load_env", lambda *a, **k: None),     # 진짜 .env 를 읽지 않는다
            mock.patch.object(ms, "_trust_done", True),                  # truststore 를 건드리지 않는다
            mock.patch.object(ms.urllib.request, "urlopen", self.net),
            mock.patch.object(ms, "data_dir", lambda *a, **k: self.data),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        os.environ.pop("NEXT_PUBLIC_SUPABASE_URL", None)
        ms._pushed.clear()
        self.addCleanup(self.tmp.cleanup)

    def queue_files(self):
        folder = self.data / "memo_queue"
        return sorted(folder.glob("*.json")) if folder.is_dir() else []

    def session_file(self, day="2026-11-25", period=3, subject="수학"):
        return self.data / "sessions" / day / f"{period}교시_{ms.safe_name(subject)}.json"


class PushTests(Base):
    def test_upsert_request_shape(self):
        s = session(memos=[
            memo("good", "발문이 좋았음", "2026-11-25T01:00:00.000Z"),
            memo("fix", "활동이 길었음", "2026-11-25T01:05:00.000Z", t="05:00"),
            memo("step", "단계: 도입", "2026-11-25T01:01:00.000Z", idx=0),
            memo("adj", "시간 조정: 도입 +1분", "2026-11-25T01:02:00.000Z", idx=0, delta=1),
            memo("student", "발표 메모(올리면 안 됨)", "2026-11-25T01:06:00.000Z"),
        ])
        result = ms.push_session(s, data=self.data)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["sent"], 4)
        self.assertEqual(len(self.net.requests), 1)
        req = self.net.requests[0]
        self.assertEqual(req["method"], "POST")
        parsed = urlparse(req["url"])
        self.assertEqual(f"{parsed.scheme}://{parsed.netloc}{parsed.path}", f"{FAKE_URL}/rest/v1/lesson_memos")
        self.assertEqual(parse_qs(parsed.query), {"on_conflict": ["memo_key"]})
        self.assertIn("resolution=ignore-duplicates", req["headers"]["prefer"])
        self.assertEqual(req["headers"]["apikey"], FAKE_KEY)
        self.assertEqual(req["headers"]["authorization"], f"Bearer {FAKE_KEY}")
        rows = req["body"]
        self.assertEqual(len(rows), 4)
        self.assertNotIn("student", {r["kind"] for r in rows})
        columns = {"date", "period", "subject", "record_key", "unit", "lesson", "title", "kind", "text", "t", "pc", "extra", "memo_key"}
        for row in rows:
            self.assertEqual(set(row), columns)
        good = next(r for r in rows if r["kind"] == "good")
        self.assertEqual((good["date"], good["period"], good["subject"], good["record_key"], good["pc"]),
                         ("2026-11-25", 3, "수학", "lesson-0001", "시험PC"))
        self.assertEqual(good["extra"], {"at": "2026-11-25T01:00:00.000Z"})
        adj = next(r for r in rows if r["kind"] == "adj")
        self.assertEqual(adj["extra"], {"at": "2026-11-25T01:02:00.000Z", "idx": 0, "delta": 1})   # idx 0 도 남아야 함
        self.assertEqual(len({r["memo_key"] for r in rows}), 4)
        self.assertEqual(self.queue_files(), [])

    def test_memo_key_is_stable_and_distinguishes(self):
        a = memo("good", "같은 글", "2026-11-25T01:00:00.000Z")
        self.assertEqual(ms.memo_key("2026-11-25", 3, "수학", a), ms.memo_key("2026-11-25", "3", "수학", dict(a)))
        self.assertNotEqual(ms.memo_key("2026-11-25", 3, "수학", a), ms.memo_key("2026-11-25", 4, "수학", a))
        self.assertNotEqual(ms.memo_key("2026-11-25", 3, "수학", a), ms.memo_key("2026-11-25", 3, "수학", {**a, "text": "다른 글"}))

    def test_second_save_does_not_resend_known_memos(self):
        s = session(memos=[memo("note", "하나", "2026-11-25T01:00:00.000Z")])
        ms.push_session(s, data=self.data)
        again = ms.push_session(s, data=self.data)
        self.assertEqual(again["status"], "nothing_new")
        self.assertEqual(len(self.net.requests), 1)
        s["memos"].append(memo("note", "둘", "2026-11-25T01:01:00.000Z"))
        ms.push_session(s, data=self.data)
        self.assertEqual(len(self.net.requests), 2)
        self.assertEqual([r["text"] for r in self.net.requests[1]["body"]], ["둘"])

    def test_failure_queues_then_next_call_resends_first(self):
        old = session(memos=[memo("fix", "나중에 올릴 것", "2026-11-25T01:00:00.000Z")])
        self.net.handler = lambda rec: (_ for _ in ()).throw(urllib.error.URLError("offline"))
        result = ms.push_session(old, data=self.data)
        self.assertEqual(result["status"], "queued")
        self.assertEqual(len(self.queue_files()), 1)
        saved = json.loads(self.queue_files()[0].read_text(encoding="utf-8"))
        self.assertEqual([r["text"] for r in saved["rows"]], ["나중에 올릴 것"])

        # 인터넷이 돌아옴 → 같은 수업이 아닌 다른 수업을 저장해도 대기열이 먼저 올라간다
        self.net.requests.clear()
        self.net.handler = lambda rec: None
        new = session(period=4, subject="국어", memos=[memo("good", "새 메모", "2026-11-25T02:00:00.000Z")])
        result = ms.push_session(new, data=self.data)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["flushed"], 1)
        self.assertEqual([[r["text"] for r in q["body"]] for q in self.net.requests], [["나중에 올릴 것"], ["새 메모"]])
        self.assertEqual(self.queue_files(), [])

    def test_offline_with_existing_queue_makes_one_request_only(self):
        self.net.handler = lambda rec: (_ for _ in ()).throw(urllib.error.URLError("offline"))
        ms.push_session(session(memos=[memo("note", "a", "2026-11-25T01:00:00.000Z")]), data=self.data)
        self.net.requests.clear()
        ms.push_session(session(period=4, subject="국어", memos=[memo("note", "b", "2026-11-25T02:00:00.000Z")]), data=self.data)
        self.assertEqual(len(self.net.requests), 1)        # 대기열 시도 1번뿐, 새 메모 요청으로 또 기다리지 않음
        self.assertEqual(len(self.queue_files()), 2)

    def test_queue_keeps_one_file_per_lesson(self):
        self.net.handler = lambda rec: (_ for _ in ()).throw(urllib.error.URLError("offline"))
        s = session(memos=[memo("note", "a", "2026-11-25T01:00:00.000Z")])
        ms.push_session(s, data=self.data)
        s["memos"].append(memo("note", "b", "2026-11-25T01:01:00.000Z"))
        ms.push_session(s, data=self.data)
        files = self.queue_files()
        self.assertEqual(len(files), 1)
        self.assertEqual([r["text"] for r in json.loads(files[0].read_text(encoding="utf-8"))["rows"]], ["a", "b"])

    def test_server_error_queues_and_poison_file_does_not_block_others(self):
        def handler(rec):
            texts = [r["text"] for r in rec["body"]]
            if "나쁜행" in texts:
                raise http_error(400)
            return None
        self.net.handler = lambda rec: (_ for _ in ()).throw(http_error(500))
        self.assertEqual(ms.push_session(session(memos=[memo("note", "나쁜행", "2026-11-25T01:00:00.000Z")]), data=self.data)["status"], "queued")
        self.assertEqual(ms.push_session(session(period=4, subject="국어", memos=[memo("note", "좋은행", "2026-11-25T02:00:00.000Z")]), data=self.data)["status"], "queued")
        self.assertEqual(len(self.queue_files()), 2)
        self.net.requests.clear()
        self.net.handler = handler
        result = ms.flush_queue(self.data)
        self.assertEqual((result["sent"], result["failed"], result["network_error"]), (1, 1, False))
        left = self.queue_files()
        self.assertEqual(len(left), 1)
        self.assertEqual(json.loads(left[0].read_text(encoding="utf-8"))["rows"][0]["text"], "나쁜행")

    def test_timeout_is_short_and_errors_never_raise(self):
        for error in (socket.timeout("slow"), TimeoutError("slow"), urllib.error.URLError(socket.timeout("slow")), ConnectionResetError("x")):
            self.net.requests.clear()
            self.net.handler = lambda rec, e=error: (_ for _ in ()).throw(e)
            result = ms.push_session(session(memos=[memo("note", "x", "2026-11-25T01:00:00.000Z")]), data=self.data)
            self.assertEqual(result["status"], "queued")
            self.assertTrue(self.net.requests)
            for rec in self.net.requests:
                self.assertLessEqual(rec["timeout"], 10)
            ms._pushed.clear()
        self.assertEqual(ms.PUSH_TIMEOUT, 5)

    def test_no_config_neither_requests_nor_queues(self):
        with mock.patch.dict(os.environ, {"SUPABASE_URL": "", "SUPABASE_SERVICE_ROLE_KEY": ""}):
            result = ms.push_session(session(memos=[memo("note", "x", "2026-11-25T01:00:00.000Z")]), data=self.data)
        self.assertEqual(result["status"], "no_config")
        self.assertEqual(self.net.requests, [])
        self.assertEqual(self.queue_files(), [])

    def test_alternative_url_name_is_used(self):
        with mock.patch.dict(os.environ, {"SUPABASE_URL": "", "NEXT_PUBLIC_SUPABASE_URL": "https://other-test.invalid/"}):
            ms.push_session(session(memos=[memo("note", "x", "2026-11-25T01:00:00.000Z")]), data=self.data)
        self.assertTrue(self.net.requests[0]["url"].startswith("https://other-test.invalid/rest/v1/lesson_memos?"))

    def test_plain_http_remote_url_is_refused(self):
        with mock.patch.dict(os.environ, {"SUPABASE_URL": "http://memo-test.invalid"}):
            result = ms.push_session(session(memos=[memo("note", "x", "2026-11-25T01:00:00.000Z")]), data=self.data)
        self.assertEqual(result["status"], "no_config")
        self.assertEqual(self.net.requests, [])

    def test_bad_session_is_skipped(self):
        self.assertEqual(ms.push_session({"date": "아님", "memos": []}, data=self.data)["status"], "skipped")
        self.assertEqual(ms.push_session({"memos": []}, data=self.data)["status"], "skipped")
        self.assertEqual(self.net.requests, [])

    def test_student_only_session_sends_nothing(self):
        s = session(memos=[memo("student", "발표", "2026-11-25T01:00:00.000Z")])
        self.assertEqual(ms.push_session(s, data=self.data)["status"], "nothing_new")
        self.assertEqual(self.net.requests, [])


class PullTests(Base):
    def row(self, day="2026-11-25", period=3, subject="수학", kind="note", text="x", at="2026-11-25T01:00:00.000Z", pc="학교", **kw):
        m = memo("note" if kind == "student" else kind, text, at, **kw.pop("extra_fields", {}))
        row = ms.rows_for_session(session(day, period, subject, [m]), pc=pc)[0]
        row["kind"] = kind     # 학생 메모는 rows_for_session 이 걸러내므로, 서버에 잘못 올라와 있는 경우를 흉내 내려고 직접 바꾼다
        row.update({"id": len(self.rows) + 1, "created_at": "2026-11-25T03:00:00+00:00"})
        row.update(kw)
        self.rows.append(row)
        return row

    def setUp(self):
        super().setUp()
        self.rows = []
        self.net.handler = self.serve

    def serve(self, rec):
        if rec["method"] != "GET":      # 올리기(POST)는 내용 없이 성공
            return None
        q = parse_qs(urlparse(rec["url"]).query)
        rows = list(self.rows)
        if "date" in q:
            rows = [r for r in rows if r["date"] >= q["date"][0].removeprefix("gte.")]
        rows.sort(key=lambda r: r["id"])
        offset, limit = int(q["offset"][0]), int(q["limit"][0])
        return rows[offset:offset + limit]

    def test_request_shape(self):
        ms.pull("2026-11-01", data=self.data)
        req = self.net.requests[0]
        self.assertEqual(req["method"], "GET")
        q = parse_qs(urlparse(req["url"]).query)
        self.assertEqual(q["date"], ["gte.2026-11-01"])
        self.assertEqual(q["order"], ["id.asc"])
        self.assertEqual(q["offset"], ["0"])
        self.assertEqual(req["headers"]["apikey"], FAKE_KEY)
        self.assertLessEqual(req["timeout"], 30)

    def test_merges_new_keeps_local_and_skips_duplicates(self):
        mine = memo("good", "이 PC 에서 쓴 것", "2026-11-25T01:00:00.000Z")
        local = session(memos=[mine, memo("fix", "아직 안 올라간 것", "2026-11-25T01:10:00.000Z")])
        local["notice"] = "알림장 초안"
        path = self.session_file()
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(local, ensure_ascii=False), encoding="utf-8")

        self.rows.append({**ms.rows_for_session(local, pc="집")[0], "id": 1, "created_at": "2026-11-25T03:00:00+00:00"})   # 이미 있는 메모
        self.row(text="학교에서 쓴 것", at="2026-11-25T01:05:00.000Z")
        self.row(kind="step", text="단계: 전개", at="2026-11-25T01:20:00.000Z", extra_fields={"idx": 1})
        self.row(kind="student", text="올라와 있으면 안 되는 학생 메모", at="2026-11-25T01:30:00.000Z")

        result = ms.pull("2026-11-01", data=self.data)
        self.assertEqual((result["status"], result["added"], result["skipped"], result["files"]), ("success", 2, 1, 1))
        merged = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(merged["notice"], "알림장 초안")                       # 다른 칸은 그대로
        self.assertEqual([m["text"] for m in merged["memos"]],
                         ["이 PC 에서 쓴 것", "학교에서 쓴 것", "아직 안 올라간 것", "단계: 전개"])   # 시간순, 내 것 보존
        self.assertEqual(merged["memos"][0], mine)
        step = merged["memos"][-1]
        self.assertEqual((step["kind"], step["idx"], step["at"], step["t"]), ("step", 1, "2026-11-25T01:20:00.000Z", "01:00"))
        self.assertNotIn("올라와 있으면 안 되는 학생 메모", path.read_text(encoding="utf-8"))

        again = ms.pull("2026-11-01", data=self.data)                          # 다시 받아도 그대로
        self.assertEqual((again["added"], again["skipped"]), (0, 3))
        self.assertEqual(json.loads(path.read_text(encoding="utf-8")), merged)

    def test_creates_file_for_lesson_written_on_other_pc(self):
        self.row(day="2026-11-24", period=5, subject="도덕", text="학교에서만 있는 수업", title="바른 생활")
        result = ms.pull(None, data=self.data)
        self.assertEqual((result["added"], result["files"]), (1, 1))
        made = json.loads(self.session_file("2026-11-24", 5, "도덕").read_text(encoding="utf-8"))
        self.assertEqual((made["date"], made["period"], made["subject"], made["title"], made["record_key"]),
                         ("2026-11-24", 5, "도덕", "바른 생활", "lesson-0001"))
        self.assertEqual([m["text"] for m in made["memos"]], ["학교에서만 있는 수업"])
        self.assertEqual(set(made["memos"][0]), {"t", "at", "kind", "text"})

    def test_pagination_reads_every_page(self):
        for i in range(5):
            self.row(text=f"m{i}", at=f"2026-11-25T01:0{i}:00.000Z")
        with mock.patch.object(ms, "PAGE", 2):
            result = ms.pull(None, data=self.data)
        self.assertEqual(result["fetched"], 5)
        self.assertEqual([parse_qs(urlparse(r["url"]).query)["offset"][0] for r in self.net.requests], ["0", "2", "4"])
        self.assertEqual(len(json.loads(self.session_file().read_text(encoding="utf-8"))["memos"]), 5)

    def test_since_filters_old_lessons(self):
        self.row(day="2026-10-01", text="옛날")
        self.row(day="2026-11-25", text="최근")
        ms.pull("2026-11-20", data=self.data)
        self.assertFalse(self.session_file("2026-10-01").exists())
        self.assertTrue(self.session_file("2026-11-25").exists())

    def test_broken_local_file_is_untouched_and_not_recorded(self):
        path = self.session_file()
        path.parent.mkdir(parents=True)
        path.write_bytes(b"{ not json")
        self.row(text="x")
        result = ms.pull(None, data=self.data)
        self.assertEqual((result["status"], result["broken"], result["added"]), ("partial", 1, 0))
        self.assertEqual(path.read_bytes(), b"{ not json")
        self.assertIsNone(ms.last_pull(self.data))

    def test_bad_rows_and_path_tricks_are_ignored(self):
        self.row(text="정상")
        self.rows.append({"id": 90, "date": "../../x", "period": 1, "subject": "수학", "kind": "note", "text": "a", "t": "", "memo_key": "k1"})
        self.rows.append({"id": 91, "date": "2026-11-25", "period": 1, "subject": "../../탈출", "kind": "note", "text": "b", "t": "", "memo_key": "k2", "extra": {}})
        result = ms.pull(None, data=self.data)
        self.assertEqual(result["ignored"], 1)
        inside = {p.resolve() for p in (self.data / "sessions").rglob("*.json")}
        self.assertTrue(all(self.data.resolve() in p.parents for p in inside))
        self.assertFalse((self.data.parent / "탈출.json").exists())

    def test_network_error_returns_error_without_raising(self):
        self.net.handler = lambda rec: (_ for _ in ()).throw(urllib.error.URLError("offline"))
        result = ms.pull(None, data=self.data)
        self.assertEqual(result["status"], "error")
        self.assertIsNone(ms.last_pull(self.data))
        self.assertLessEqual(self.net.requests[0]["timeout"], 30)

    def test_records_last_pull_and_if_older_runs_once_a_day(self):
        self.row(text="x")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(ms.main(["pull", "--if-older", "24", "--days", "3650"]), 0)
        self.assertTrue(self.net.requests)
        self.assertIsNotNone(ms.last_pull(self.data))
        self.net.requests.clear()
        with contextlib.redirect_stdout(out):
            self.assertEqual(ms.main(["pull", "--if-older", "24"]), 0)
        self.assertEqual(self.net.requests, [])                                # 24시간 안 → 요청 없음
        stale = (datetime.now().astimezone() - timedelta(hours=25)).isoformat(timespec="seconds")
        (self.data / "memo_sync_state.json").write_text(json.dumps({"last_pull": stale}), encoding="utf-8")
        with contextlib.redirect_stdout(out):
            self.assertEqual(ms.main(["pull", "--if-older", "24", "--days", "3650"]), 0)
        self.assertTrue(self.net.requests)                                     # 25시간 지남 → 다시 받음

    def test_pull_command_flushes_queue_first(self):
        self.net.handler = lambda rec: (_ for _ in ()).throw(urllib.error.URLError("offline"))
        ms.push_session(session(memos=[memo("note", "밀린 것", "2026-11-25T01:00:00.000Z")]), data=self.data)
        self.net.requests.clear()
        self.net.handler = self.serve
        with contextlib.redirect_stdout(io.StringIO()):
            ms.main(["pull", "--all"])
        self.assertEqual([r["method"] for r in self.net.requests][:2], ["POST", "GET"])
        self.assertEqual(self.queue_files(), [])


class SecretTests(Base):
    def test_key_and_address_never_appear_in_output_or_results(self):
        seen = []
        for error in (urllib.error.URLError(f"cannot reach {FAKE_URL} with {FAKE_KEY}"), http_error(401), TimeoutError(FAKE_URL)):
            self.net.handler = lambda rec, e=error: (_ for _ in ()).throw(e)
            ms._pushed.clear()
            seen.append(json.dumps(ms.push_session(session(memos=[memo("note", "x", "2026-11-25T01:00:00.000Z")]), data=self.data), ensure_ascii=False))
            seen.append(json.dumps(ms.pull(None, data=self.data), ensure_ascii=False))
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                ms.main(["pull", "--all"])
                ms.main(["flush"])
            seen += [out.getvalue(), err.getvalue()]
        for text in seen:
            self.assertNotIn(FAKE_KEY, text)
            self.assertNotIn("memo-test.invalid", text)
        for path in self.data.rglob("*"):
            if path.is_file():
                body = path.read_text(encoding="utf-8")
                self.assertNotIn(FAKE_KEY, body)
                self.assertNotIn("memo-test.invalid", body)


if __name__ == "__main__":
    unittest.main()
