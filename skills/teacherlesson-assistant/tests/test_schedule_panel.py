"""📅 일정·할 일 칸(T107). 가짜 시트만 쓴다 — 실제 시트·네트워크·gspread 없이 돈다."""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys
import threading
from datetime import date, timedelta

import pytest

SKILL = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL))
sys.path.insert(0, str(SKILL.parent / "_shared"))
import schedule_panel as panel  # noqa: E402

WED = date(2026, 11, 25)  # 수요일
FRI = date(2026, 11, 27)


def row(day, text, category="학교", status="", target="전체"):
    return {"키": text, "날짜": day if isinstance(day, str) else day.isoformat(), "구분": category,
            "내용": text, "상태": status, "출처": "수동", "대상": target}


def texts(entries):
    return [e["text"] for e in entries]


def test_today_events_in_message_order_without_tasks():
    rows = [row(WED, "알림 하나", "공지"), row(WED, "학교 행사"), row(WED, "출장 하나", "출장"),
            row(WED, "내 할 일", "개인"), row(WED + timedelta(days=1), "내일 행사")]
    got = panel.build(rows, WED)
    assert texts(got["today"]) == ["출장 하나", "학교 행사", "알림 하나"]
    assert got["date"] == "2026-11-25" and got["reason"] == ""


def test_checked_waiting_other_grade_and_broken_rows_are_hidden():
    rows = [row(WED, "끝낸 것", status="✔"), row(WED, "검토 중", status="검토대기"),
            row(WED, "다른 학년", target="타학년·유치원"), row("날짜 아님", "날짜 없는 것"), row(WED, ""),
            row(WED, "끝낸 할 일", "개인", status="✔"), row(WED, "보이는 것"),
            row(WED, "구분 빈 것", "")]
    got = panel.build(rows, WED)
    assert texts(got["today"]) == ["보이는 것", "구분 빈 것"]
    assert got["today"][1]["category"] == "학교"
    assert got["tasks"] == []


def test_week_runs_to_sunday_and_includes_tomorrow():
    sunday = date(2026, 11, 29)
    rows = [row(sunday + timedelta(days=1), "다음 주 월"), row(sunday, "일요일"), row(WED + timedelta(days=1), "내일"),
            row(WED, "오늘"), row(WED - timedelta(days=1), "어제"), row(FRI, "금 할 일", "개인")]
    got = panel.build(rows, WED)
    assert texts(got["week"]) == ["내일", "일요일"]
    assert got["week"][0]["when"] == "11/26(목)"
    assert got["week_label"] == "이번 주 남은 일정"


def test_friday_shows_weekend_and_next_week():
    rows = [row(date(2026, 11, 28), "토"), row(date(2026, 12, 4), "다음 주 금"), row(date(2026, 12, 6), "다음 주 일"),
            row(date(2026, 12, 7), "그다음 월")]
    got = panel.build(rows, FRI)
    assert texts(got["week"]) == ["토", "다음 주 금", "다음 주 일"]
    assert got["week_label"] == "주말·다음 주 일정"


def test_tasks_late_today_and_within_30_days():
    rows = [row(WED + timedelta(days=31), "너무 먼 것", "개인"), row(WED + timedelta(days=30), "30일 뒤", "개인"),
            row(WED + timedelta(days=1), "내일까지", "개인"), row(WED, "오늘까지", "개인"),
            row(WED - timedelta(days=2), "지난 것", "개인"), row(WED - timedelta(days=2), "지난 행사")]
    got = panel.build(rows, WED)
    assert [(t["text"], t["dday"], t["left"]) for t in got["tasks"]] == [
        ("지난 것", "D+2", -2), ("오늘까지", "D-day", 0), ("내일까지", "D-1", 1), ("30일 뒤", "D-30", 30)]
    assert got["due_today"] == 2


def test_summary_counts_only_never_contents():
    rows = [row(WED, "비밀 출장지", "출장"), row(WED, "행사"), row(WED - timedelta(days=1), "지난 일", "개인"),
            row(WED + timedelta(days=1), "가", "개인"), row(WED + timedelta(days=1), "나", "개인"),
            row(WED + timedelta(days=5), "다", "개인")]
    summary = panel.build(rows, WED)["summary"]
    assert summary == "오늘 출장 1 · 학교 1 · 지난 할 일 1 · 할 일 D-1 2건"


def test_empty_sheet_summary():
    assert panel.build([], WED)["summary"] == "오늘 행사 없음"


def test_same_rows_as_morning_message():
    """아침 메시지에 나오는 오늘 항목은 칸에도 오늘 행사나 할 일로 나온다."""
    panel._todo("message")
    from schooltodo.message import build_message

    rows = [row(WED, "출장 가", "출장"), row(WED, "할 일 나", "개인"), row(WED, "제외", status="✔"),
            row(WED, "남의 것", target="타학년·유치원"), row(WED - timedelta(days=3), "늦은 다", "개인")]
    lines, _count = build_message(rows, WED, task_day=None)
    got = panel.build(rows, WED)
    shown = texts(got["today"]) + texts(got["tasks"])
    for name in ("출장 가", "할 일 나", "늦은 다"):
        assert name in shown and any(name in line for line in lines)
    for name in ("제외", "남의 것"):
        assert name not in shown and not any(name in line for line in lines)


def test_reading_needs_no_extra_package_and_a_missing_one_is_named(monkeypatch):
    panel._todo("message")
    for name in ("requests", "schooltodo.inbox", "schooltodo.sync", "schooltodo.sources"):
        monkeypatch.setitem(sys.modules, name, None)  # 설치 안 된 것처럼
    import schooltodo

    for name in ("inbox", "sync", "sources"):
        monkeypatch.delattr(schooltodo, name, raising=False)
    assert texts(panel.build([row(WED, "행사")], WED)["today"]) == ["행사"]
    got = panel.Panel(lambda: pytest.fail("시트를 열면 안 됨"), Clock()).quick({"text": "할 일", "confirm": True}, WED)
    assert got["written"] is False and "schooltodo.inbox" in got["message"]


class FakeSheet:
    def __init__(self):
        self.calls = []

    def append_row(self, values, **options):
        self.calls.append((values, options))


class FakeDb:
    def __init__(self, rows=(), error=None, with_inbox=True):
        self.data, self.error, self.sheet = list(rows), error, FakeSheet()
        self.with_inbox, self.reads = with_inbox, 0

    def rows(self):
        self.reads += 1
        if self.error:
            raise self.error
        return self.data

    def inbox(self):
        panel._todo("inbox")
        from schooltodo.inbox import InboxSheet

        return InboxSheet(self.sheet) if self.with_inbox else None


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def test_cache_for_ten_minutes_and_refresh():
    db, clock = FakeDb([row(WED, "행사")]), Clock()
    p = panel.Panel(lambda: db, clock)
    assert texts(p.agenda(WED)["today"]) == ["행사"]
    clock.now += 599
    p.agenda(WED)
    assert db.reads == 1
    p.agenda(WED, refresh=True)
    assert db.reads == 2
    clock.now += 600
    p.agenda(WED)
    assert db.reads == 3


def test_cached_rows_are_recounted_on_the_next_day():
    db = FakeDb([row(WED + timedelta(days=1), "내일 행사")])
    p = panel.Panel(lambda: db, Clock())
    assert p.agenda(WED)["today"] == []
    assert texts(p.agenda(WED + timedelta(days=1))["today"]) == ["내일 행사"]
    assert db.reads == 1


@pytest.mark.parametrize("error, expected", [
    (SystemExit("일정DB 시트에 접근할 수 없습니다(403). 확인하세요.\n  서비스 계정: robot@example.invalid"),
     "일정DB 시트에 접근할 수 없습니다(403). 확인하세요."),
    (ValueError("일정DB 첫 행에 열 이름이 없습니다: 날짜"), "일정DB 첫 행에 열 이름이 없습니다: 날짜"),
    (ModuleNotFoundError("No module named 'gspread'"),
     "일정 시트를 읽으려면 gspread 가 필요해요: python -m pip install gspread"),
    (RuntimeError("https://sheets.example.invalid/SHEET-ID"),
     "일정 시트에 연결하지 못했어요(RuntimeError). 인터넷과 school-todo-kakao 설정을 확인해 주세요."),
])
def test_failure_gives_empty_lists_and_easy_reason(error, expected):
    p = panel.Panel(lambda: FakeDb(error=error), Clock())
    got = p.agenda(WED)
    assert got["reason"] == expected
    assert got["today"] == got["week"] == got["tasks"] == [] and got["due_today"] == 0


def test_failure_is_retried_after_a_minute():
    db, clock = FakeDb([row(WED, "행사")], error=OSError("끊김")), Clock()
    p = panel.Panel(lambda: db, clock)
    assert p.agenda(WED)["reason"]
    db.error = None
    clock.now += 59
    assert p.agenda(WED)["reason"] and db.reads == 1
    clock.now += 1
    assert p.agenda(WED)["reason"] == "" and db.reads == 2


def test_quick_without_confirm_writes_nothing():
    db = FakeDb()
    opened = []
    p = panel.Panel(lambda: opened.append(1) or db, Clock())
    for body in ({"text": "내일 상담 준비"}, {"text": "내일 상담 준비", "confirm": "true"},
                 {"text": "내일 상담 준비", "confirm": 1}):
        got = p.quick(body, WED)
        assert got["written"] is False and got["status"] == "success"
        assert got["parsed"] == {"date": "2026-11-26", "when": "11/26(목)", "category": "개인", "text": "상담 준비"}
    assert opened == [] and db.sheet.calls == []


def test_quick_confirmed_appends_one_raw_line():
    db = FakeDb()
    got = panel.Panel(lambda: db, Clock()).quick({"text": "  =11/30  출장\n복명 ", "confirm": True}, WED)
    assert got["written"] is True and "sync" in got["message"]
    assert db.sheet.calls == [(["=11/30 출장 복명"], {"value_input_option": "RAW", "table_range": "A1"})]
    assert got["parsed"]["category"] == "출장"


@pytest.mark.parametrize("text, part", [
    ("", "적어 주세요"), ("   ", "적어 주세요"), (None, "적어 주세요"), ("내일", "내용"),
    ("11/20 지난 일", "지난 날짜"), ("가" * 201, "200자"),
])
def test_quick_rejects_bad_lines_before_opening_the_sheet(text, part):
    db = FakeDb()
    got = panel.Panel(lambda: db, Clock()).quick({"text": text, "confirm": True}, WED)
    assert got["status"] == "error" and got["written"] is False and part in got["message"]
    assert db.sheet.calls == []


def test_quick_without_inbox_tab_or_with_write_failure():
    got = panel.Panel(lambda: FakeDb(with_inbox=False), Clock()).quick({"text": "할 일", "confirm": True}, WED)
    assert got["written"] is False and "빠른입력" in got["message"]
    db = FakeDb()

    def broken(*_a, **_k):
        raise OSError("끊김")

    db.sheet.append_row = broken
    got = panel.Panel(lambda: db, Clock()).quick({"text": "할 일", "confirm": True}, WED)
    assert got == {"status": "error", "written": False,
                   "message": "일정 시트에 연결하지 못했어요(OSError). 인터넷과 school-todo-kakao 설정을 확인해 주세요."}


def test_quick_line_is_what_sync_will_read():
    """칸에서 적은 줄을 sync 의 plan_inbox 가 그대로 일정DB 행으로 만든다."""
    db = FakeDb()
    panel.Panel(lambda: db, Clock()).quick({"text": "다음주 화요일 공문 마감", "confirm": True}, WED)
    from schooltodo.inbox import plan_inbox

    rows, marks = plan_inbox([(2, db.sheet.calls[0][0][0])], set(), WED)
    assert marks == {2: "✔ 반영"} and rows[0]["날짜"] == "2026-12-01" and rows[0]["내용"] == "공문 마감"


def test_only_sheet_settings_are_copied_and_existing_values_win():
    environ = {"DB_TAB": "이미 있음"}
    panel.apply_settings({"DB_SHEET_ID": "가짜", "DB_TAB": "새 값", "KAKAO_REFRESH_TOKEN": "가짜 토큰",
                          "MY_NAME": "교사A", "INBOX_TAB": ""}, environ)
    assert environ == {"DB_SHEET_ID": "가짜", "DB_TAB": "이미 있음"}


def test_relative_key_file_is_looked_up_beside_the_central_env(tmp_path, monkeypatch):
    panel._todo("envload")
    from schooltodo import envload

    monkeypatch.setattr(envload, "ENV_DIRS", [])
    panel.apply_settings({}, {}, env_dir=tmp_path)
    panel.apply_settings({}, {}, env_dir=tmp_path)
    (tmp_path / "key.json").write_text("{}", encoding="utf-8")
    assert envload.ENV_DIRS == [tmp_path]
    assert envload.resolve_path("key.json") == tmp_path / "key.json"


@pytest.mark.skipif(not shutil.which("node"), reason="node 가 없어 화면 함수 시험(test_agenda.js)을 건너뜀")
def test_screen_functions_in_node():
    got = subprocess.run([shutil.which("node"), str(SKILL / "tests" / "test_agenda.js")],
                         capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert got.returncode == 0, got.stderr
    assert "통과" in got.stdout


@pytest.fixture
def server(monkeypatch, tmp_path):
    """수업 비서 서버를 빈 포트에 띄우고, 일정 칸만 가짜 시트로 바꾼다."""
    import http.client
    import json
    from http.server import ThreadingHTTPServer

    monkeypatch.setenv("MY_SKILLS_DATA_DIR", str(tmp_path))
    import assistant_server as app

    db = FakeDb([row(date.today(), "오늘 행사")])
    monkeypatch.setattr(panel, "PANEL", panel.Panel(lambda: db, Clock()))
    srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    def call(method, url, body=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", srv.server_port, timeout=10)
        conn.request(method, url, json.dumps(body).encode() if body is not None else None, headers or {})
        res = conn.getresponse()
        data = res.read().decode("utf-8")
        conn.close()
        return res.status, data

    yield db, call, json.loads
    srv.shutdown()
    srv.server_close()


def test_server_routes(server):
    db, call, load = server
    status, script = call("GET", "/agenda.js")
    assert status == 200 and "function breakLine" in script
    assert '<script src="/agenda.js"></script>' in call("GET", "/")[1]
    status, data = call("GET", "/api/agenda")
    assert status == 200 and texts(load(data)["today"]) == ["오늘 행사"]
    call("GET", "/api/agenda")
    assert db.reads == 1
    call("GET", "/api/agenda?refresh=1")
    assert db.reads == 2
    got = load(call("POST", "/api/agenda/add", {"text": "내일 할 일"})[1])
    assert got["written"] is False and db.sheet.calls == []
    got = load(call("POST", "/api/agenda/add", {"text": "내일 할 일", "confirm": True})[1])
    assert got["written"] is True and db.sheet.calls[0][0] == ["내일 할 일"]


def test_other_sites_cannot_read_or_write_the_sheet(server):
    db, call, _load = server
    evil = {"Origin": "https://evil.example"}
    assert call("GET", "/api/agenda", headers=evil)[0] == 403
    assert call("POST", "/api/agenda/add", {"text": "할 일", "confirm": True}, evil)[0] == 403
    assert db.reads == 0 and db.sheet.calls == []
