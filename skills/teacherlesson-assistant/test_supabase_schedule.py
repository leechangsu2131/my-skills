"""supabase_schedule.py 시험. 진짜 Supabase 대신 PostgREST 흉내를 내는 가짜 서버(이 PC 안, 임시 포트)만 쓴다.

    python -m unittest test_supabase_schedule -v      (이 폴더에서)

안전장치: 중앙 .env 를 읽지 않고(load_env 를 막음) 주소·키를 가짜 값으로 바꾼다. setUp 에서 접속 주소가
127.0.0.1 인지 확인하므로 실제 DB 에는 읽기도 쓰기도 가지 않는다. 표준 라이브러리 + requests 만 쓴다
(PDF 시험만 PyMuPDF 가 있을 때 돈다).
"""
import json
import os
import pathlib
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import supabase_schedule as sm  # noqa: E402

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover
    fitz = None


class FakeDB:
    """표 이름 → 행 목록. 요청 기록과 '다음 요청을 실패시키기' 기능이 있다."""

    def __init__(self):
        self.tables = {}
        self.log = []          # (METHOD, table, query dict)
        self.fail = {}         # (METHOD, table) -> HTTP 상태
        self.counter = 0

    def next_id(self):
        self.counter += 1
        return f"new-{self.counter}"

    def by_id(self, table, row_id):
        return next(r for r in self.tables[table] if r["id"] == row_id)


class Handler(BaseHTTPRequestHandler):
    db: FakeDB = None

    def log_message(self, *args):
        pass

    def _reply(self, code, payload):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _parts(self):
        u = urlparse(self.path)
        return u.path.rsplit("/", 1)[-1], {k: v[0] for k, v in parse_qs(u.query).items()}

    def _fail(self, method, table):
        code = self.db.fail.get((method, table))
        if code:
            self._reply(code, {"message": "forced failure"})
            return True
        return False

    def _embed(self, table, row, select):
        db = self.db
        if table == "lesson_slots" and "lesson:lesson_lessons" in select:
            lesson = next((l for l in db.tables["lesson_lessons"] if l["id"] == row.get("lesson_id")), None)
            row["lesson"] = self._lesson_out(lesson, select) if lesson else None
        elif table == "lesson_lessons" and "subject:lesson_subjects" in select:
            row.update(self._lesson_out(row, select))
        return row

    def _lesson_out(self, lesson, select):
        db = self.db
        out = dict(lesson)
        subj = next((s for s in db.tables["lesson_subjects"] if s["id"] == lesson.get("subject_id")), None)
        unit = next((u for u in db.tables["lesson_units"] if u["id"] == lesson.get("unit_id")), None)
        out["subject"] = {"id": subj["id"], "name": subj["name"], "color": subj.get("color")} if subj else None
        out["unit"] = {"name": unit["name"]} if unit else None
        return out

    def do_GET(self):
        table, q = self._parts()
        self.db.log.append(("GET", table, q))
        if self._fail("GET", table):
            return
        rows = [dict(r) for r in self.db.tables.get(table, [])]
        for col, val in q.items():
            if col in ("select", "order", "limit", "offset"):
                continue
            if val.startswith("eq."):
                rows = [r for r in rows if str(r.get(col)) == val[3:]]
        for col in reversed([c for c in q.get("order", "").split(",") if c]):
            rows.sort(key=lambda r, c=col: (r.get(c) is None, r.get(c) if r.get(c) is not None else 0))
        offset, limit = int(q.get("offset", 0)), int(q.get("limit", 1000))
        rows = rows[offset:offset + limit]
        select = q.get("select", "*")
        self._reply(200, [self._embed(table, r, select) for r in rows])

    def do_PATCH(self):
        table, q = self._parts()
        self.db.log.append(("PATCH", table, q))
        if self._fail("PATCH", table):
            return
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        target = q["id"][3:]
        out = []
        for row in self.db.tables[table]:
            if str(row["id"]) == target:
                row.update(body)
                out.append(dict(row))
        self._reply(200, out)

    def do_POST(self):
        table, q = self._parts()
        self.db.log.append(("POST", table, q))
        if self._fail("POST", table):
            return
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        added = []
        for item in (body if isinstance(body, list) else [body]):
            row = {"id": self.db.next_id(), **item}
            self.db.tables[table].append(row)
            added.append(dict(row))
        self._reply(201, added)


def fixture():
    """수학 4차시(날짜 11/23·25·30, 12/2 한 교시씩) + 국어 1차시 + 아직 날짜 없는 수학 5차시."""
    db = FakeDB()
    db.tables["lesson_subjects"] = [
        {"id": "s-math", "name": "수학", "color": "#e85d04"},
        {"id": "s-kor", "name": "국어", "color": "#005bbf"},
    ]
    db.tables["lesson_units"] = [
        {"id": "u-6", "name": "6. 그림그래프"},
        {"id": "u-k1", "name": "1. 독서"},
    ]
    def lesson(i, subj, unit, n, title, sort, pdf=None, start=None, end=None):
        return {"id": f"L{i}", "legacy_lesson_id": f"lesson-{i:04d}", "subject_id": subj, "unit_id": unit,
                "lesson_number": n, "title": title, "pdf_path": pdf, "start_page": start, "end_page": end,
                "note": None, "extension_count": 0, "sort_order": sort}
    db.tables["lesson_lessons"] = [
        lesson(1, "s-math", "u-6", 1, "수학1", 1), lesson(2, "s-math", "u-6", 2, "수학2", 2),
        lesson(3, "s-math", "u-6", 3, "수학3", 3), lesson(4, "s-math", "u-6", 4, "수학4", 4),
        lesson(5, "s-math", "u-6", 5, "수학5(날짜 없음)", 5),
        lesson(9, "s-kor", "u-k1", 1, "국어1", 9),
    ]
    def slot(sid, lid, day, period, status="planned", order=1, source="progress_sync"):
        return {"id": sid, "lesson_id": lid, "slot_date": day, "slot_period": period, "slot_order": order,
                "status": status, "source": source, "memo": None}
    db.tables["lesson_slots"] = [
        slot("sA", "L1", "2026-11-23", 4), slot("sB", "L2", "2026-11-25", 4),
        slot("sC", "L3", "2026-11-30", 4), slot("sD", "L4", "2026-12-02", 4),
        slot("sK", "L9", "2026-11-24", 2),
    ]
    return db


class FakeServerCase(unittest.TestCase):
    def setUp(self):
        self.db = fixture()
        handler = type("H", (Handler,), {"db": self.db})
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True).start()
        url = f"http://127.0.0.1:{self.server.server_address[1]}"
        patches = [
            mock.patch.dict(os.environ, {"SUPABASE_URL": url, "SUPABASE_SERVICE_ROLE_KEY": "fake-key",
                                         "NO_PROXY": "127.0.0.1,localhost", "no_proxy": "127.0.0.1,localhost"}),
            mock.patch.object(sm, "load_env", lambda *a, **k: None),   # 중앙 .env(진짜 키) 읽기 차단
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        # 안전장치: 진짜 DB 로 가는 일이 없도록 접속 주소를 확인한다.
        self.assertTrue(sm._client()[0].startswith("http://127.0.0.1:"), "가짜 서버가 아닌 주소로 접속하려 함")
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def slot(self, sid):
        return self.db.by_id("lesson_slots", sid)

    def writes(self):
        return [(m, t) for m, t, _ in self.db.log if m != "GET"]


class DayScheduleTest(FakeServerCase):
    def test_reads_one_day_in_legacy_shape(self):
        rows = sm.day_schedule(sm.date(2026, 11, 23))
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual((r["period"], r["subject"], r["unit"], r["lesson"], r["title"]),
                         (4, "수학", "6. 그림그래프", "1", "수학1"))
        self.assertEqual((r["record_key"], r["slot_id"], r["status"], r["has_pdf"]), ("lesson-0001", "sA", "planned", False))
        self.assertNotIn("_lesson_sort", r)

    def test_periods_sorted_and_other_days_excluded(self):
        self.db.tables["lesson_slots"].append(
            {"id": "sX", "lesson_id": "L9", "slot_date": "2026-11-23", "slot_period": 2, "slot_order": 1,
             "status": "planned", "source": "x", "memo": None})
        rows = sm.day_schedule(sm.date(2026, 11, 23))
        self.assertEqual([r["period"] for r in rows], [2, 4])

    def test_planned_beats_done_in_same_period(self):
        # 완료된 쪽이 교육과정 순서로 더 뒤(4차시)여도, 예정인 1차시가 보여야 한다
        self.slot("sA")["status"] = "planned"
        self.db.tables["lesson_slots"].append(
            {"id": "sDone", "lesson_id": "L4", "slot_date": "2026-11-23", "slot_period": 4, "slot_order": 2,
             "status": "done", "source": "x", "memo": None})
        rows = sm.day_schedule(sm.date(2026, 11, 23))
        self.assertEqual([(r["slot_id"], r["lesson"], r["status"]) for r in rows], [("sA", "1", "planned")])

    def test_all_done_shows_latest_lesson_in_curriculum_order(self):
        # 같은 날·교시에 1차시와 4차시가 모두 완료 → 4차시가 1차시를 가리지 않는다(2026-11-23 실제 사례)
        self.slot("sA")["status"] = "done"
        self.db.tables["lesson_slots"].append(
            {"id": "sD2", "lesson_id": "L4", "slot_date": "2026-11-23", "slot_period": 4, "slot_order": 2,
             "status": "done", "source": "x", "memo": None})
        rows = sm.day_schedule(sm.date(2026, 11, 23))
        self.assertEqual([(r["slot_id"], r["lesson"]) for r in rows], [("sD2", "4")])

    def test_empty_day(self):
        self.assertEqual(sm.day_schedule(sm.date(2026, 12, 25)), [])

    def test_has_pdf_flag(self):
        self.db.by_id("lesson_lessons", "L1")["pdf_path"] = "D:\\지도서\\수학.pdf"
        self.assertTrue(sm.day_schedule(sm.date(2026, 11, 23))[0]["has_pdf"])


class ReadersTest(FakeServerCase):
    def test_upcoming_lists_subject_lessons_in_order(self):
        self.slot("sA")["status"] = "done"
        rows = sm.upcoming("수학")
        self.assertEqual([r["lesson"] for r in rows], ["1", "2", "3", "4", "5"])
        by = {r["lesson"]: r for r in rows}
        self.assertTrue(by["1"]["done"])
        self.assertFalse(by["2"]["done"])
        self.assertEqual((by["2"]["planned_date"], by["2"]["planned_period"], by["2"]["slot_id"]), ("2026-11-25", 4, "sB"))
        self.assertEqual(by["5"]["planned_date"], "")           # 날짜 없는 차시
        self.assertFalse(by["5"]["done"])                       # 칸이 없으면 '함'이 아니다
        self.assertEqual(by["2"]["unit"], "6. 그림그래프")
        self.assertEqual(by["2"]["record_key"], "lesson-0002")

    def test_upcoming_unknown_subject(self):
        self.assertEqual(sm.upcoming("체육"), [])

    def test_records_legacy_columns(self):
        self.slot("sA")["status"] = "done"
        recs = {r["lesson_id"]: r for r in sm.records()}
        self.assertEqual(len(recs), 6)
        one = recs["lesson-0001"]
        self.assertEqual((one["과목"], one["대단원"], one["차시"], one["수업내용"], one["실행여부"]),
                         ("수학", "6. 그림그래프", "1", "수학1", True))
        two = recs["lesson-0002"]
        self.assertEqual((two["계획일"], two["계획교시"], two["실행여부"]), ("2026-11-25", 4, False))
        self.assertEqual(recs["lesson-0005"]["계획일"], "")

    def test_reads_more_than_one_page(self):
        self.db.tables["lesson_slots"] += [
            {"id": f"f{i}", "lesson_id": "L9", "slot_date": "2027-01-01", "slot_period": 1, "slot_order": i,
             "status": "planned", "source": "x", "memo": None} for i in range(2400)]
        rows = sm._get("lesson_slots")
        self.assertEqual(len(rows), 2405)
        pages = [q for m, t, q in self.db.log if m == "GET" and t == "lesson_slots"]
        self.assertEqual([q["offset"] for q in pages], ["0", "1000", "2000"])


class ErrorTest(FakeServerCase):
    def test_read_failure_is_korean_runtime_error(self):
        self.db.fail[("GET", "lesson_slots")] = 500
        with self.assertRaisesRegex(RuntimeError, r"조회 실패 \(500\)"):
            sm.day_schedule(sm.date(2026, 11, 23))

    def test_write_failure_is_korean_runtime_error(self):
        self.db.fail[("PATCH", "lesson_slots")] = 403
        with self.assertRaisesRegex(RuntimeError, r"갱신 실패 \(403\)"):
            sm.progress("done", {"subject": "수학", "slot_id": "sA"})

    def test_missing_settings(self):
        with mock.patch.dict(os.environ, {"SUPABASE_URL": "", "NEXT_PUBLIC_SUPABASE_URL": ""}):
            with self.assertRaisesRegex(RuntimeError, "SUPABASE_URL"):
                sm._client()
        with mock.patch.dict(os.environ, {"SUPABASE_SERVICE_ROLE_KEY": ""}):
            with self.assertRaisesRegex(RuntimeError, "SERVICE_ROLE_KEY"):
                sm._client()

    def test_unknown_action(self):
        res = sm.progress("explode", {"subject": "수학"})
        self.assertEqual(res["status"], "error")
        self.assertEqual(self.writes(), [])


class DoneTest(FakeServerCase):
    def test_done_by_slot_id(self):
        res = sm.progress("done", {"subject": "수학", "slot_id": "sB"})
        self.assertEqual((res["status"], res["updated"]), ("success", 1))
        self.assertEqual([self.slot(s)["status"] for s in ("sA", "sB", "sC")], ["planned", "done", "planned"])

    def test_done_by_record_key_and_date(self):
        res = sm.progress("done", {"subject": "수학", "record_key": "lesson-0003", "target_date": "2026-11-30"})
        self.assertEqual(res["status"], "success")
        self.assertEqual(self.slot("sC")["status"], "done")

    def test_done_wrong_date_changes_nothing(self):
        res = sm.progress("done", {"subject": "수학", "record_key": "lesson-0003", "target_date": "2026-11-29"})
        self.assertEqual(res["status"], "error")
        self.assertEqual(self.writes(), [])

    def test_concurrent_done_requests_do_not_write_from_the_same_snapshot(self):
        row = {
            "id": "slot-lock",
            "status": "planned",
            "slot_date": "2026-11-25",
            "lesson": {"legacy_lesson_id": "lesson-0001", "subject": {"name": "수학"}},
        }
        first_read = threading.Event()
        release_first = threading.Event()
        second_started = threading.Event()
        guard = threading.Lock()
        read_count = 0
        write_count = 0

        def read_slots():
            nonlocal read_count
            with guard:
                read_count += 1
                number = read_count
            if number == 1:
                first_read.set()
                if not release_first.wait(timeout=3):
                    raise AssertionError("첫 요청 해제 대기 시간 초과")
            return [{**row, "lesson": dict(row["lesson"], subject=dict(row["lesson"]["subject"]))}]

        def write_slot(table, row_id, values):
            nonlocal write_count
            with guard:
                write_count += 1
                row.update(values)
            return [dict(row)]

        def send(is_second=False):
            if is_second:
                second_started.set()
            return sm.progress("done", {"subject": "수학", "slot_id": "slot-lock"})

        with (
            mock.patch.object(sm, "_slots_joined", side_effect=read_slots),
            mock.patch.object(sm, "_patch", side_effect=write_slot),
            ThreadPoolExecutor(max_workers=2) as pool,
        ):
            first = pool.submit(send)
            self.assertTrue(first_read.wait(timeout=2))
            second = pool.submit(send, True)
            self.assertTrue(second_started.wait(timeout=2))
            self.assertEqual(read_count, 1, "첫 요청이 끝나기 전에 두 번째 요청이 자료를 읽으면 안 됨")
            release_first.set()
            first_result = first.result(timeout=2)
            second_result = second.result(timeout=2)

        self.assertEqual(first_result["status"], "success")
        self.assertEqual(second_result["status"], "error")
        self.assertEqual(read_count, 2)
        self.assertEqual(write_count, 1)
        self.assertEqual(row["status"], "done")

    def test_done_already_done_is_not_found(self):
        self.slot("sA")["status"] = "done"
        res = sm.progress("done", {"subject": "수학", "slot_id": "sA"})
        self.assertEqual(res["status"], "error")


class PushTest(FakeServerCase):
    def test_push_moves_only_subject_planned_slots_from_date(self):
        # 기준일 11/24: 국어 슬롯(11/24)은 기준일 이후지만 과목이 달라 움직이면 안 된다
        res = sm.progress("push", {"subject": "수학", "from_date": "2026-11-24", "days": 3})
        self.assertEqual((res["status"], res["updated"]), ("success", 3))
        self.assertEqual(self.slot("sB")["slot_date"], "2026-11-28")
        self.assertEqual(self.slot("sC")["slot_date"], "2026-12-03")
        self.assertEqual(self.slot("sD")["slot_date"], "2026-12-05")
        self.assertEqual(self.slot("sA")["slot_date"], "2026-11-23")       # 기준일 앞 날짜는 그대로
        self.assertEqual(self.slot("sK")["slot_date"], "2026-11-24")       # 다른 과목은 그대로

    def test_push_skips_done_slots(self):
        self.slot("sC")["status"] = "done"
        res = sm.progress("push", {"subject": "수학", "from_date": "2026-11-23", "days": 1})
        self.assertEqual(res["updated"], 3)                               # A, B, D
        self.assertEqual(self.slot("sC")["slot_date"], "2026-11-30")

    def test_push_bad_input(self):
        for bad in ({"days": "x", "from_date": "2026-11-30"}, {"days": 2, "from_date": "11/30"}, {"days": 2}):
            res = sm.progress("push", {"subject": "수학", **bad})
            self.assertEqual(res["status"], "error", bad)
        self.assertEqual(self.writes(), [])


class ExtendTest(FakeServerCase):
    def test_extend_inserts_a_slot_and_shifts_the_rest(self):
        res = sm.progress("extend", {"subject": "수학", "slot_id": "sA"})
        self.assertEqual((res["status"], res["updated"]), ("success", 4))   # 새 칸 1 + B·C·D 이동 3
        math = sorted((s for s in self.db.tables["lesson_slots"] if s["lesson_id"] != "L9"),
                      key=lambda s: (s["slot_date"], s["slot_order"]))
        self.assertEqual([(s["slot_date"], s["lesson_id"]) for s in math], [
            ("2026-11-23", "L1"), ("2026-11-25", "L1"), ("2026-11-30", "L2"),
            ("2026-12-02", "L3"), ("2026-12-04", "L4")])
        new = next(s for s in math if s["id"].startswith("new-"))
        self.assertEqual((new["status"], new["source"], new["slot_period"]), ("planned", "manual_extend", 4))

    def test_extend_does_not_touch_other_subjects(self):
        sm.progress("extend", {"subject": "수학", "slot_id": "sA"})
        self.assertEqual(self.slot("sK")["slot_date"], "2026-11-24")

    def test_extend_without_planned_target_is_an_error(self):
        self.slot("sA")["status"] = "done"
        res = sm.progress("extend", {"subject": "수학", "slot_id": "sA"})
        self.assertEqual(res["status"], "error")
        self.assertEqual(self.writes(), [])

    def test_extend_wrong_subject_is_an_error(self):
        res = sm.progress("extend", {"subject": "국어", "slot_id": "sA"})
        self.assertEqual(res["status"], "error")
        self.assertEqual(self.writes(), [])


class CatchUpTest(FakeServerCase):
    """'여기부터 다시 잡기'(catch-up). 2026-11-24 부터의 동작(ISSUE-029):
    - 교사가 고른 차시를 **요청 날짜(target_date)의 그 과목 칸**으로 옮긴다. 그날 칸이 없으면 그날 이후 첫 예정 칸.
    - 교육과정 순서(sort_order)가 고른 차시보다 앞서는 예정 차시는 모두 완료 처리한다(달력 날짜가 아니라 차시 순서 기준).
    - 요청에 target_date 가 없거나 날짜 모양이 틀리면 오류이고, 아무것도 쓰지 않는다.
    기준 자료(fixture): 수학 L1~L4 가 11/23·25·30·12/2 의 4교시, L5 는 날짜 없음, 국어 L9 는 11/24 2교시."""

    def catch_up(self, key, day, subject="수학", **extra):
        return sm.progress("catch-up", {"subject": subject, "record_key": key, "target_date": day, **extra})

    def math_slots(self):
        return sorted((s for s in self.db.tables["lesson_slots"] if s["lesson_id"] != "L9"),
                      key=lambda s: (s["slot_date"], s["slot_period"], s["slot_order"]))

    def test_catch_up_moves_selected_lesson_to_the_requested_day(self):
        # 국어 차시의 순서값을 수학 차시보다 작게 해 두어야, 코드가 과목을 가리지 않고 '앞 차시'를 완료 처리하는 잘못을 잡을 수 있다.
        self.db.by_id("lesson_lessons", "L9")["sort_order"] = 0
        res = self.catch_up("lesson-0003", "2026-11-25")
        self.assertEqual((res["status"], res["completed"]), ("success", 2))
        self.assertEqual((self.slot("sA")["status"], self.slot("sB")["status"]), ("done", "done"))   # 앞 차시 L1·L2 완료
        c = self.slot("sC")
        self.assertEqual((c["slot_date"], c["slot_period"], c["slot_order"], c["status"], c["source"]),
                         ("2026-11-25", 4, 2, "planned", "manual_catch_up"))     # 오늘(11/25) 4교시, 이미 있던 칸 뒤
        self.assertEqual(self.slot("sD")["slot_date"], "2026-12-02")        # 뒤 차시 날짜는 그대로
        k = self.slot("sK")                                                 # 다른 과목은 건드리지 않음
        self.assertEqual((k["slot_date"], k["slot_period"], k["status"]), ("2026-11-24", 2, "planned"))

    def test_catch_up_first_lesson_completes_nothing(self):
        res = self.catch_up("lesson-0001", "2026-11-23")
        self.assertEqual((res["status"], res["completed"]), ("success", 0))
        self.assertEqual([self.slot(s)["status"] for s in ("sA", "sB", "sC", "sD")], ["planned"] * 4)
        a = self.slot("sA")
        self.assertEqual((a["slot_date"], a["slot_period"], a["slot_order"]), ("2026-11-23", 4, 1))
        self.assertEqual([self.slot(s)["slot_date"] for s in ("sB", "sC", "sD")],
                         ["2026-11-25", "2026-11-30", "2026-12-02"])

    def test_catch_up_unscheduled_lesson_gets_a_new_slot_on_the_requested_day(self):
        res = self.catch_up("lesson-0005", "2026-11-23")
        self.assertEqual((res["status"], res["completed"]), ("success", 4))     # L1~L4 가 모두 앞 차시
        self.assertEqual([self.slot(s)["status"] for s in ("sA", "sB", "sC", "sD")], ["done"] * 4)
        new = [s for s in self.db.tables["lesson_slots"] if s["id"].startswith("new-")]
        self.assertEqual(len(new), 1)
        n = new[0]
        self.assertEqual((n["lesson_id"], n["slot_date"], n["slot_period"], n["slot_order"], n["status"], n["source"]),
                         ("L5", "2026-11-23", 4, 2, "planned", "manual_catch_up"))

    def test_catch_up_back_to_a_done_lesson_reopens_it(self):
        self.slot("sA")["status"] = "done"
        res = self.catch_up("lesson-0001", "2026-11-23")
        self.assertEqual((res["status"], res["completed"]), ("success", 0))
        a = self.slot("sA")
        self.assertEqual((a["status"], a["source"], a["slot_date"], a["slot_period"], a["slot_order"]),
                         ("planned", "manual_catch_up", "2026-11-23", 4, 1))
        self.assertEqual(self.slot("sB")["status"], "planned")

    def test_catch_up_day_without_a_slot_uses_the_first_planned_slot_after_it(self):
        # 11/24 에는 수학 칸이 없다(국어만). 그날 이후 첫 예정 수학 칸은 11/25 4교시.
        res = self.catch_up("lesson-0003", "2026-11-24")
        self.assertEqual((res["status"], res["completed"]), ("success", 2))
        c = self.slot("sC")
        self.assertEqual((c["slot_date"], c["slot_period"], c["slot_order"], c["status"]),
                         ("2026-11-25", 4, 2, "planned"))
        self.assertEqual((self.slot("sK")["slot_date"], self.slot("sK")["status"]), ("2026-11-24", "planned"))

    def test_catch_up_forward_keeps_later_lessons_in_curriculum_order(self):
        # 고른 차시 L3 을 11/25 로 당긴 뒤: 남은 예정 차시는 L3 → L4 순서이고, 같은 날·교시·칸에 겹친 슬롯이 없다.
        self.catch_up("lesson-0003", "2026-11-25")
        planned = [s["lesson_id"] for s in self.math_slots() if s["status"] == "planned"]
        self.assertEqual(planned, ["L3", "L4"])
        places = [(s["slot_date"], s["slot_period"], s["slot_order"]) for s in self.math_slots()]
        self.assertEqual(len(places), len(set(places)))

    @unittest.expectedFailure
    def test_catch_up_to_an_earlier_lesson_shows_it_on_the_requested_day(self):
        """알려진 문제(ISSUE-031, 고치지 않고 기록만): 11/25 4교시에는 L2 가 이미 예정이다. 교사가 더 앞 차시 L1 을
        '오늘 할 차시'로 고르면 L1 이 같은 칸의 뒤(slot_order 2)에 들어가고, day_schedule 은 같은 교시의 예정 차시 중
        교육과정 순서가 더 뒤인 L2 를 보여 준다. 응답은 success 인데 화면에는 L1 이 나오지 않는다.
        코드 주석의 의도('선택한 차시를 오늘 수업으로 만든다')대로 고쳐지면 이 시험이 통과하므로 expectedFailure 를 지운다."""
        res = self.catch_up("lesson-0001", "2026-11-25")
        self.assertEqual(res["status"], "success")
        shown = {row["period"]: row["record_key"] for row in sm.day_schedule(date(2026, 11, 25))}
        self.assertEqual(shown[4], "lesson-0001")

    def test_catch_up_without_a_valid_date_is_an_error_and_writes_nothing(self):
        for bad in ("", "11/25", "2026-13-45"):
            res = self.catch_up("lesson-0003", bad)
            self.assertEqual(res["status"], "error", bad)
        res = sm.progress("catch-up", {"subject": "수학", "record_key": "lesson-0003"})    # target_date 자체가 없음
        self.assertEqual(res["status"], "error")
        self.assertEqual(self.writes(), [])

    def test_catch_up_unknown_lesson_is_an_error_and_writes_nothing(self):
        res = self.catch_up("lesson-9999", "2026-11-25")
        self.assertEqual(res["status"], "error")
        self.assertEqual(self.writes(), [])

    def test_catch_up_lesson_of_another_subject_is_an_error_and_writes_nothing(self):
        for subject in ("국어", "영어", ""):        # 다른 과목·없는 과목·과목 빠짐
            res = self.catch_up("lesson-0003", "2026-11-25", subject=subject)
            self.assertEqual(res["status"], "error", subject)
        self.assertEqual(self.writes(), [])

    def test_catch_up_no_planned_slot_left_after_the_day_is_an_error(self):
        for s in self.db.tables["lesson_slots"]:
            if s["lesson_id"] != "L9":
                s["status"] = "done"
        res = self.catch_up("lesson-0005", "2026-11-24")          # 그날 수학 칸도 없고, 그 뒤 예정 칸도 없음
        self.assertEqual(res["status"], "error")
        self.assertEqual(self.writes(), [])

    def test_catch_up_uses_an_existing_slot_of_the_day_even_if_it_is_done(self):
        # 모두 완료여도 그날(11/23) 수학 칸이 있으면 그 칸의 4교시 뒤에 새 칸을 만든다(오류가 아님).
        for s in self.db.tables["lesson_slots"]:
            if s["lesson_id"] != "L9":
                s["status"] = "done"
        res = self.catch_up("lesson-0005", "2026-11-23")
        self.assertEqual((res["status"], res["completed"]), ("success", 0))
        n = next(s for s in self.db.tables["lesson_slots"] if s["id"].startswith("new-"))
        self.assertEqual((n["lesson_id"], n["slot_date"], n["slot_period"], n["slot_order"]),
                         ("L5", "2026-11-23", 4, 2))


class PdfTest(FakeServerCase):
    def test_lesson_not_found(self):
        with self.assertRaisesRegex(FileNotFoundError, "경로"):
            sm.pdf_for_lesson("lesson-9999")

    def test_lesson_without_pdf_path(self):
        with self.assertRaisesRegex(FileNotFoundError, "경로"):
            sm.pdf_for_lesson("lesson-0001")

    def _fake_schedule(self):
        mod = mock.MagicMock()
        mod.resolve_pdf_path = lambda p: p
        return mock.patch.dict(sys.modules, {"schedule": mod})

    def test_missing_file_on_this_pc(self):
        self.db.by_id("lesson_lessons", "L1")["pdf_path"] = str(pathlib.Path(tempfile.gettempdir()) / "없는파일.pdf")
        with self._fake_schedule(), self.assertRaisesRegex(FileNotFoundError, "찾지 못했어요"):
            sm.pdf_for_lesson("lesson-0001")

    @unittest.skipUnless(fitz, "PyMuPDF 가 없어 건너뜀")
    def test_cuts_pages_from_a_whole_guide_and_keeps_split_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            whole = pathlib.Path(tmp) / "지도서.pdf"
            doc = fitz.open()
            for i in range(6):
                doc.new_page().insert_text((72, 72), f"page {i + 1}")
            doc.save(str(whole)); doc.close()
            split_dir = pathlib.Path(tmp) / "pdf_splits"
            split_dir.mkdir()
            split = split_dir / "차시.pdf"
            split.write_bytes(whole.read_bytes())

            self.db.by_id("lesson_lessons", "L1").update(pdf_path=str(whole), start_page=2, end_page=3)
            self.db.by_id("lesson_lessons", "L2").update(pdf_path=str(split), start_page=2, end_page=3)
            with self._fake_schedule():
                cut = sm.pdf_for_lesson("lesson-0001")
                kept = sm.pdf_for_lesson("lesson-0002")
            with fitz.open(stream=cut, filetype="pdf") as d:
                self.assertEqual(d.page_count, 2)
                self.assertIn("page 2", d[0].get_text())
            with fitz.open(stream=kept, filetype="pdf") as d:
                self.assertEqual(d.page_count, 6)                       # 이미 잘린 파일은 통째로

            self.db.by_id("lesson_lessons", "L3").update(pdf_path=str(whole), start_page=5, end_page=3)
            with self._fake_schedule(), self.assertRaisesRegex(FileNotFoundError, "쪽수"):
                sm.pdf_for_lesson("lesson-0003")


if __name__ == "__main__":
    unittest.main()
