"""assistant_server.py 의 '연결 함수' 시험 (S1): fetch_schedule · upcoming · recent_memos · copy_secret ·
start_prepare · ask_prepare.

    python -m pytest tests/test_server_glue.py -v      (teacherlesson-assistant 폴더에서)

진짜 네트워크·Supabase·PowerShell·탐색기·Gemini 는 쓰지 않는다. urlopen·subprocess 는 가짜,
DATA·SESSIONS 등은 임시 폴더. 소스(assistant_server.py)는 고치지 않는다.
"""
import io
import json
import pathlib
import sys
import types
import urllib.error
from datetime import date, timedelta

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import assistant_server as app  # noqa: E402
import prepare_lessons  # noqa: E402

DAY = date(2026, 11, 25)


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def json_response(payload):
    return FakeResponse(json.dumps(payload, ensure_ascii=False).encode("utf-8"))


def http_error(code):
    return urllib.error.HTTPError("http://x", code, "err", {}, io.BytesIO(b""))


# ── fetch_schedule ──

LEGACY = {"schedule_backend": "sheet", "schedule_api": "http://127.0.0.1:5000/"}


def dash(items):
    return {"views": [{"id": "agenda", "data": []}, {"id": "thisweek", "data": items}]}


def item(period, subject="수학", status="planned", day=DAY, **over):
    base = {"planned_date": f"{day.isoformat()} 00:00", "planned_period": period, "subject": subject,
            "unit": "3단원", "lesson": "2", "title": f"{subject} 수업", "record_key": f"k-{subject}-{period}",
            "status": status, "pdf_path": "x.pdf"}
    base.update(over)
    return base


def serve(monkeypatch, payload=None, exc=None, seen=None):
    def fake(url, timeout=0):
        if seen is not None:
            seen.append(url)
        if exc:
            raise exc
        return json_response(payload)
    monkeypatch.setattr(app.urllib.request, "urlopen", fake)


def test_supabase_backend_is_the_default_and_names_its_source(monkeypatch):
    fake = types.SimpleNamespace(day_schedule=lambda day: [{"period": 1, "subject": "국어"}])
    monkeypatch.setitem(sys.modules, "supabase_schedule", fake)
    lessons, source = app.fetch_schedule({}, DAY)
    assert lessons == [{"period": 1, "subject": "국어"}] and source == "Supabase 진도표"


def test_supabase_failure_returns_empty_list_and_error_source_without_raising(monkeypatch, capsys):
    def boom(day):
        raise RuntimeError("연결 안 됨")
    monkeypatch.setitem(sys.modules, "supabase_schedule", types.SimpleNamespace(day_schedule=boom))
    lessons, source = app.fetch_schedule({"schedule_backend": "supabase"}, DAY)
    assert lessons == [] and source == "Supabase 연결 오류"
    assert "RuntimeError" in capsys.readouterr().err


def test_legacy_backend_reads_only_that_day_sorted_by_period(monkeypatch):
    seen = []
    serve(monkeypatch, dash([item("3교시", "사회"), item("1교시", "국어"), item("2교시", "수학", day=DAY + timedelta(days=1))]), seen=seen)
    lessons, source = app.fetch_schedule(LEGACY, DAY)
    assert source == "진도표"
    assert [(l["period"], l["subject"]) for l in lessons] == [(1, "국어"), (3, "사회")]
    assert seen == ["http://127.0.0.1:5000/api/dashboard?board_date=2026-11-25"]   # 끝의 / 는 떼고 날짜를 붙임
    assert lessons[0]["has_pdf"] is True and lessons[0]["record_key"] == "k-국어-1교시"


def test_legacy_same_period_prefers_planned_over_done(monkeypatch):
    serve(monkeypatch, dash([item("2교시", "수학", status="done", title="한 것"), item("2교시", "수학", status="planned", title="할 것")]))
    lessons, _ = app.fetch_schedule(LEGACY, DAY)
    assert [l["title"] for l in lessons] == ["할 것"]


def test_legacy_same_period_keeps_first_when_both_planned(monkeypatch):
    serve(monkeypatch, dash([item("2교시", "수학", title="먼저"), item("2교시", "수학", title="나중")]))
    lessons, _ = app.fetch_schedule(LEGACY, DAY)
    assert [l["title"] for l in lessons] == ["먼저"]


def test_legacy_future_day_hides_done_lessons(monkeypatch):
    future = date.today() + timedelta(days=3)
    serve(monkeypatch, dash([item("1교시", "국어", status="done", day=future), item("2교시", "수학", day=future)]))
    lessons, _ = app.fetch_schedule(LEGACY, future)
    assert [l["subject"] for l in lessons] == ["수학"]


def test_legacy_past_day_keeps_done_lessons(monkeypatch):
    serve(monkeypatch, dash([item("1교시", "국어", status="done")]))
    lessons, _ = app.fetch_schedule(LEGACY, DAY)   # DAY 는 지난 날짜
    assert [l["status"] for l in lessons] == ["done"]


def test_legacy_lessons_without_period_are_all_kept_and_sorted_last(monkeypatch):
    serve(monkeypatch, dash([item("", "도덕"), item("", "미술"), item("1교시", "국어")]))
    lessons, _ = app.fetch_schedule(LEGACY, DAY)
    assert [l["subject"] for l in lessons] == ["국어", "도덕", "미술"]


@pytest.mark.parametrize("exc", [urllib.error.URLError("꺼짐"), OSError("x"), ValueError("깨진 JSON")])
def test_legacy_server_down_falls_back_to_basic_timetable(monkeypatch, exc):
    serve(monkeypatch, exc=exc)
    cfg = {**LEGACY, "fallback_timetable": {str(DAY.isoweekday()): ["국어", "", "수학"]}}
    lessons, source = app.fetch_schedule(cfg, DAY)
    assert source == "기본 시간표(진도 서버 꺼짐)"
    assert [(l["period"], l["subject"]) for l in lessons] == [(1, "국어"), (3, "수학")]   # 빈 칸은 건너뛰고 교시는 칸 번호
    assert all(l["has_pdf"] is False and l["record_key"] == "" for l in lessons)


def test_legacy_server_down_without_fallback_table_is_empty(monkeypatch):
    serve(monkeypatch, exc=urllib.error.URLError("꺼짐"))
    assert app.fetch_schedule(LEGACY, DAY) == ([], "기본 시간표(진도 서버 꺼짐)")


# ── upcoming ──

def serve_many(monkeypatch, table):
    """주소 조각에 따라 다른 답. 값이 예외면 던진다."""
    def fake(url, timeout=0):
        for part, value in table.items():
            if part in url:
                if isinstance(value, Exception):
                    raise value
                return json_response(value)
        raise AssertionError(f"예상 밖 주소: {url}")
    monkeypatch.setattr(app.urllib.request, "urlopen", fake)


def lessons_list(n_done, n_open):
    return ([{"record_key": f"d{i}", "done": True} for i in range(n_done)]
            + [{"record_key": f"o{i}", "done": False} for i in range(n_open)])


def test_upcoming_supabase_keeps_last_30_done_before_first_open(monkeypatch):
    items = lessons_list(50, 5) + [{"record_key": None, "done": False}]
    monkeypatch.setattr(app, "load_config", lambda: {})
    monkeypatch.setitem(sys.modules, "supabase_schedule", types.SimpleNamespace(upcoming=lambda subject: items))
    got = app.upcoming("수학")
    assert len(got) == 30 + 6
    assert got[0]["record_key"] == "d20" and got[30]["record_key"] == "o0"
    assert got[-1]["record_key"] == ""        # None 은 빈 글자로


def test_upcoming_supabase_all_done_returns_last_30(monkeypatch):
    monkeypatch.setattr(app, "load_config", lambda: {})
    monkeypatch.setitem(sys.modules, "supabase_schedule", types.SimpleNamespace(upcoming=lambda subject: lessons_list(40, 0)))
    got = app.upcoming("수학")
    assert len(got) == 30 and got[0]["record_key"] == "d10"


def test_upcoming_legacy_window_is_30_before_and_80_after(monkeypatch):
    monkeypatch.setattr(app, "load_config", lambda: LEGACY)
    serve_many(monkeypatch, {"/api/lessons?subject=": {"items": lessons_list(50, 200)}})
    got = app.upcoming("수학")
    assert len(got) == 30 + 80 and got[0]["record_key"] == "d20" and got[-1]["record_key"] == "o79"


def test_upcoming_legacy_quotes_the_subject_in_the_url(monkeypatch):
    seen = []
    monkeypatch.setattr(app, "load_config", lambda: LEGACY)
    monkeypatch.setattr(app.urllib.request, "urlopen", lambda url, timeout=0: (seen.append(url), json_response({"items": []}))[1])
    app.upcoming("국어 활동")
    assert seen == ["http://127.0.0.1:5000/api/lessons?subject=%EA%B5%AD%EC%96%B4%20%ED%99%9C%EB%8F%99"]


def test_upcoming_legacy_other_http_error_becomes_korean_value_error(monkeypatch):
    monkeypatch.setattr(app, "load_config", lambda: LEGACY)
    serve_many(monkeypatch, {"/api/lessons": http_error(500)})
    with pytest.raises(ValueError, match="진도 서버 오류\\(500\\)"):
        app.upcoming("수학")


def test_upcoming_old_legacy_server_404_falls_back_to_agenda(monkeypatch):
    agenda = [{"subject": "수학", "status": "planned", "record_key": 7, "unit": "3단원", "lesson": "2",
               "title": "덧셈", "planned_date": "2026-11-26 00:00", "planned_period": "2교시"},
              {"subject": "수학", "status": "DONE", "record_key": "x"},       # 대소문자 상관없이 완료는 제외
              {"subject": "국어", "status": "planned", "record_key": "y"}]    # 다른 과목은 제외
    monkeypatch.setattr(app, "load_config", lambda: LEGACY)
    serve_many(monkeypatch, {"/api/lessons": http_error(404),
                             "/api/dashboard": {"views": [{"id": "agenda", "data": agenda}]}})
    assert app.upcoming("수학") == [{"record_key": "7", "unit": "3단원", "lesson": "2", "title": "덧셈",
                                    "planned_date": "2026-11-26", "planned_period": "2교시"}]


def test_upcoming_agenda_is_cut_to_40(monkeypatch):
    agenda = [{"subject": "수학", "status": "planned", "record_key": str(n)} for n in range(60)]
    monkeypatch.setattr(app, "load_config", lambda: LEGACY)
    serve_many(monkeypatch, {"/api/lessons": http_error(404), "/api/dashboard": {"views": [{"id": "agenda", "data": agenda}]}})
    assert len(app.upcoming("수학")) == 40


# ── recent_memos ──

@pytest.fixture
def sessions(tmp_path, monkeypatch):
    root = tmp_path / "sessions"
    monkeypatch.setattr(app, "SESSIONS", root)
    return root


def put(root, day, name, record):
    path = root / day / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")


def memo(kind, text):
    return {"kind": kind, "text": text}


def test_recent_memos_newest_first_and_only_useful_kinds(sessions):
    put(sessions, "2026-11-20", "2교시_수학.json", {"subject": "수학", "date": "2026-11-20", "title": "옛",
                                                  "memos": [memo("fix", "예전 고칠점")]})
    put(sessions, "2026-11-24", "2교시_수학.json", {"subject": "수학", "date": "2026-11-24", "title": "최근",
                                                  "memos": [memo("good", "잘됨"), memo("student", "숨김"), memo("star", "별"), memo("note", "메모")]})
    got = app.recent_memos("수학")
    assert [(m["date"], m["kind"], m["text"]) for m in got] == [
        ("2026-11-24", "good", "잘됨"), ("2026-11-24", "note", "메모"), ("2026-11-20", "fix", "예전 고칠점")]
    assert got[0]["title"] == "최근"


def test_recent_memos_other_subject_with_similar_file_name_is_skipped(sessions):
    # 파일 이름 패턴(수학*)에 걸려도 안의 과목이 다르면 가져오지 않는다
    put(sessions, "2026-11-24", "1교시_수학익힘.json", {"subject": "수학익힘", "memos": [memo("fix", "다른 과목")]})
    put(sessions, "2026-11-24", "2교시_수학.json", {"subject": "수학", "memos": [memo("fix", "내 과목")]})
    assert [m["text"] for m in app.recent_memos("수학")] == ["내 과목"]


def test_recent_memos_stops_after_the_file_that_reaches_the_limit(sessions):
    for n in range(5):
        put(sessions, f"2026-11-2{n}", "2교시_수학.json", {"subject": "수학", "memos": [memo("fix", f"{n}a"), memo("fix", f"{n}b")]})
    got = app.recent_memos("수학", limit=3)
    assert [m["text"] for m in got] == ["4a", "4b", "3a"]     # 한 파일은 다 읽고, 결과는 limit 개로 자름


def test_recent_memos_does_not_read_more_files_once_the_limit_is_reached(sessions, monkeypatch):
    for n in range(5):
        put(sessions, f"2026-11-2{n}", "2교시_수학.json", {"subject": "수학", "memos": [memo("fix", f"{n}a"), memo("fix", f"{n}b")]})
    reads = []
    real = app.read_json
    monkeypatch.setattr(app, "read_json", lambda path, default: (reads.append(path.parent.name), real(path, default))[1])
    app.recent_memos("수학", limit=3)
    assert reads == ["2026-11-24", "2026-11-23"]          # 둘째 파일에서 4개가 되어 멈춤 — 옛 기록을 다 읽지 않는다


def test_recent_memos_ignores_unreadable_files_and_missing_memos(sessions):
    put(sessions, "2026-11-24", "2교시_수학.json", {"subject": "수학"})
    path = sessions / "2026-11-23" / "2교시_수학.json"
    path.parent.mkdir(parents=True)
    path.write_text("{깨짐", encoding="utf-8")
    assert app.recent_memos("수학") == []


def test_recent_memos_without_any_sessions_is_empty(sessions):
    assert app.recent_memos("수학") == []


# ── copy_secret ──

class Recorder:
    def __init__(self):
        self.runs, self.timers = [], []


@pytest.fixture
def clipboard(monkeypatch):
    rec = Recorder()
    monkeypatch.setattr(app.subprocess, "run", lambda *a, **k: rec.runs.append((a, k)))

    class FakeTimer:
        def __init__(self, seconds, fn):
            rec.timers.append((seconds, fn))

        def start(self):
            rec.started = True
    monkeypatch.setattr(app.threading, "Timer", FakeTimer)
    return rec


def cfg_with_secret(prefix="MUSIC"):
    return {"subjects": {"음악": {"secret_prefix": prefix}, "수학": {}}}


@pytest.mark.parametrize("subject,field", [("수학", "id"), ("없는과목", "id"), ("음악", "email"), ("음악", "")])
def test_copy_secret_rejects_unknown_subject_or_field(monkeypatch, clipboard, subject, field):
    monkeypatch.setattr(app, "load_config", lambda: cfg_with_secret())
    with pytest.raises(ValueError, match="저장된 로그인 정보가 없어요"):
        app.copy_secret(subject, field)
    assert clipboard.runs == []


def test_copy_secret_missing_env_key_names_the_key_but_not_a_value(monkeypatch, clipboard):
    monkeypatch.setattr(app, "load_config", lambda: cfg_with_secret())
    monkeypatch.delenv("MUSIC_ID", raising=False)
    monkeypatch.setattr(app, "env_values", lambda skill: {})
    with pytest.raises(ValueError, match="MUSIC_ID"):
        app.copy_secret("음악", "id")
    assert clipboard.runs == []


def test_copy_secret_puts_value_only_in_clipboard_and_never_in_the_reply(monkeypatch, clipboard):
    monkeypatch.setattr(app, "load_config", lambda: cfg_with_secret())
    monkeypatch.setenv("MUSIC_PW", "가짜-비밀값")
    message = app.copy_secret("음악", "pw")
    (args, kwargs), = clipboard.runs
    assert kwargs["input"] == "가짜-비밀값" and "Set-Clipboard" in args[0][-1]
    assert "가짜-비밀값" not in message and "비밀번호" in message and "30초" in message
    assert clipboard.timers[0][0] == 30 and clipboard.timers[0][1] is app._clear_clipboard


def test_copy_secret_id_uses_the_ID_key_and_environment_wins_over_env_file(monkeypatch, clipboard):
    monkeypatch.setattr(app, "load_config", lambda: cfg_with_secret())
    monkeypatch.setattr(app, "env_values", lambda skill: {"MUSIC_ID": "파일값"})
    monkeypatch.setenv("MUSIC_ID", "환경값")
    assert "아이디" in app.copy_secret("음악", "id")
    assert clipboard.runs[0][1]["input"] == "환경값"


def test_copy_secret_falls_back_to_central_env_file(monkeypatch, clipboard):
    monkeypatch.setattr(app, "load_config", lambda: cfg_with_secret())
    monkeypatch.delenv("MUSIC_ID", raising=False)
    monkeypatch.setattr(app, "env_values", lambda skill: {"MUSIC_ID": "파일값"})
    app.copy_secret("음악", "id")
    assert clipboard.runs[0][1]["input"] == "파일값"


def test_clear_clipboard_overwrites_with_a_blank(monkeypatch):
    calls = []
    monkeypatch.setattr(app.subprocess, "run", lambda *a, **k: calls.append((a, k)))
    app._clear_clipboard()
    assert "Set-Clipboard -Value ' '" in calls[0][0][0][-1] and calls[0][1]["check"] is False


# ── start_prepare ──

@pytest.fixture
def prep(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(app, "DATA", data)
    monkeypatch.setattr(prepare_lessons, "STATUS", data / "prepare_status.json")
    launched = []

    class FakeProc:
        pid = 4242

    def fake_popen(args, **kwargs):
        launched.append((args, kwargs))
        return FakeProc()
    monkeypatch.setattr(app.subprocess, "Popen", fake_popen)
    return types.SimpleNamespace(data=data, launched=launched)


def test_start_prepare_launches_script_and_marks_running_with_a_token(prep):
    result = app.start_prepare({"date": "2026-11-25"})
    assert result["status"] == "success"
    (args, kwargs), = prep.launched
    assert args[1].endswith("prepare_lessons.py") and args[2:] == ["--date", "2026-11-25"]
    status = json.loads(prepare_lessons.STATUS.read_text(encoding="utf-8"))
    assert status["running"] is True and status["pid"] == 4242 and status["date"] == "2026-11-25" and status["items"] == []
    assert status["token"] and kwargs["env"]["PREPARE_TOKEN"] == status["token"]   # 스크립트가 자기 표시로 알아보는 열쇠
    assert kwargs["env"]["PYTHONIOENCODING"] == "utf-8"


def test_start_prepare_redo_adds_the_flag(prep):
    app.start_prepare({"date": "2026-11-25", "redo": True})
    assert prep.launched[0][0][-1] == "--redo"


def test_start_prepare_refuses_when_already_running_and_starts_nothing(prep, monkeypatch):
    monkeypatch.setattr(prepare_lessons, "is_running", lambda status: True)
    result = app.start_prepare({"date": "2026-11-25"})
    assert result["status"] == "error" and "이미 수업 준비가 돌고 있어요" in result["message"]
    assert prep.launched == []


def test_start_prepare_refuses_when_another_request_won_the_race(prep, monkeypatch):
    answers = iter([False, True])        # 첫 확인은 비었는데, 잠금 안에서 다시 보니 다른 요청이 먼저 시작함
    monkeypatch.setattr(prepare_lessons, "is_running", lambda status: next(answers))
    result = app.start_prepare({"date": "2026-11-25"})
    assert result["status"] == "error" and prep.launched == []


@pytest.mark.parametrize("bad", ["", "11/25", "2026-13-40", None])
def test_start_prepare_rejects_a_bad_date_before_anything_happens(prep, bad):
    with pytest.raises(ValueError):
        app.start_prepare({"date": bad})
    assert prep.launched == [] and not prepare_lessons.STATUS.exists()


# ── ask_prepare ──

@pytest.fixture
def ask(tmp_path, monkeypatch):
    data = tmp_path / "data"
    units, notebooklm = data / "units", data / "notebooklm"
    units.mkdir(parents=True)
    notebooklm.mkdir()
    monkeypatch.setattr(app, "DATA", data)
    monkeypatch.setattr(app, "UNITS", units)
    monkeypatch.setattr(app, "NOTEBOOKLM", notebooklm)
    monkeypatch.setattr(app, "CAUTIONS_PATH", tmp_path / "cautions.json")
    monkeypatch.setattr(app, "load_config", lambda: {"subjects": {"수학": {"publisher": "가출판"}}})
    monkeypatch.setattr(app, "find_unit", lambda lesson: None)
    opened = []
    monkeypatch.setattr(app.subprocess, "Popen", lambda args, **k: opened.append(args))
    return types.SimpleNamespace(data=data, units=units, notebooklm=notebooklm, opened=opened)


def ask_body(**over):
    base = {"date": "2026-11-25", "period": 2, "subject": "수학", "unit": "3. 분수", "lesson": "2",
            "title": "분수의 덧셈", "record_key": "lesson-0002"}
    base.update(over)
    return base


def use_pdf(monkeypatch, data):
    monkeypatch.setitem(sys.modules, "supabase_schedule", types.SimpleNamespace(pdf_for_lesson=lambda key: data))


def test_ask_prepare_collects_unit_overview_lesson_pdf_and_note(ask, monkeypatch):
    (ask.units / "개관.pdf").write_bytes(b"%PDF-1 overview")
    monkeypatch.setattr(app, "find_unit", lambda lesson: {"overview_pdf": "개관.pdf"})
    use_pdf(monkeypatch, b"%PDF-1.7 lesson")
    note = app.lesson_note_path("수학", "3. 분수", 2)
    note.parent.mkdir(parents=True)
    note.write_text("노트", encoding="utf-8")
    result = app.ask_prepare(ask_body())
    assert result["files"] == ["1_단원개관_3._분수.pdf", "2_차시지도서_2차시.pdf", "3_NotebookLM노트_2차시.md"]
    assert result["missing"] == [] and "(없음" not in result["message"]
    folder = ask.data / "ask" / "2026-11-25" / "2교시_수학"
    assert (folder / "2_차시지도서_2차시.pdf").read_bytes() == b"%PDF-1.7 lesson"
    assert (folder / "질문.txt").read_text(encoding="utf-8") == result["prompt"]
    assert ask.opened == [["explorer", str(folder)]]
    assert "「분수의 덧셈」" in result["prompt"] and "출판사: 가출판" in result["prompt"]
    assert "첨부: 1_단원개관_3._분수.pdf" in result["prompt"]


def test_ask_prepare_reports_what_is_missing(ask, monkeypatch):
    use_pdf(monkeypatch, "<html>로그인 페이지</html>".encode())      # PDF 가 아닌 답(%PDF- 로 시작 안 함)은 저장하지 않는다
    result = app.ask_prepare(ask_body())
    assert result["files"] == [] and result["missing"] == ["단원 개관 PDF", "차시 지도서 PDF"]
    assert "(없음: 단원 개관 PDF, 차시 지도서 PDF)" in result["message"]
    assert "첨부:" not in result["prompt"]
    assert not list((ask.data / "ask").rglob("*.pdf"))


def test_ask_prepare_without_record_key_cannot_fetch_the_lesson_pdf(ask, monkeypatch):
    use_pdf(monkeypatch, b"%PDF-should-not-be-asked")
    result = app.ask_prepare(ask_body(record_key=""))
    assert result["missing"] == ["단원 개관 PDF", "차시 지도서 PDF"] and result["files"] == []


def test_ask_prepare_pdf_fetch_failure_is_listed_not_raised(ask, monkeypatch):
    def boom(key):
        raise OSError("서버 꺼짐")
    monkeypatch.setitem(sys.modules, "supabase_schedule", types.SimpleNamespace(pdf_for_lesson=boom))
    result = app.ask_prepare(ask_body())
    assert "차시 지도서 PDF(진도 서버 확인)" in result["missing"] and result["status"] == "success"


def test_ask_prepare_legacy_backend_downloads_the_pdf_from_the_progress_server(ask, monkeypatch):
    monkeypatch.setattr(app, "load_config", lambda: {"schedule_backend": "sheet", "schedule_api": "http://127.0.0.1:5000/"})
    seen = []
    monkeypatch.setattr(app.urllib.request, "urlopen", lambda url, timeout=0: (seen.append(url), FakeResponse(b"%PDF-1 old"))[1])
    result = app.ask_prepare(ask_body())
    assert seen == ["http://127.0.0.1:5000/api/pdf/lesson-0002"] and "2_차시지도서_2차시.pdf" in result["files"]


@pytest.mark.parametrize("key", ["../etc", "a b", "한글", "x" * 41, "a/b"])
def test_ask_prepare_rejects_odd_record_keys_before_touching_the_disk(ask, key):
    with pytest.raises(ValueError, match="차시 번호 형식"):
        app.ask_prepare(ask_body(record_key=key))
    assert not (ask.data / "ask").exists() and ask.opened == []


def test_ask_prepare_rejects_a_bad_date(ask):
    with pytest.raises(ValueError):
        app.ask_prepare(ask_body(date="어제"))


def test_ask_prepare_keeps_the_folder_inside_data_even_with_a_hostile_subject(ask, monkeypatch):
    use_pdf(monkeypatch, b"%PDF-1")
    app.ask_prepare(ask_body(subject="../../밖", period="1"))
    inside = ask.data / "ask" / "2026-11-25"
    folders = list(inside.iterdir())
    assert len(folders) == 1 and folders[0].resolve().is_relative_to(ask.data.resolve())
    assert not (ask.data.parent / "밖").exists()


def test_ask_prepare_adds_at_most_five_cautions(ask, monkeypatch):
    (ask.data.parent / "cautions.json").write_text(json.dumps(
        {"가출판|수학": [{"text": f"주의{n}"} for n in range(4)], "가출판|*": [{"text": f"공통{n}"} for n in range(4)]}, ensure_ascii=False), encoding="utf-8")
    use_pdf(monkeypatch, b"%PDF-1")
    prompt = app.ask_prepare(ask_body())["prompt"]
    shown = prompt.split("느낀 점:")[1].strip().splitlines()
    assert shown == ["- 주의0", "- 주의1", "- 주의2", "- 주의3", "- 공통0"]       # 앞에서 5개만(출판사별 → 공통 순)


def test_ask_prepare_notebooklm_mode_collects_no_files(ask):
    result = app.ask_prepare(ask_body(mode="notebooklm"))
    assert result["files"] == [] and result["status"] == "success"
    assert "분수의 덧셈" in result["prompt"]
    assert not (ask.data / "ask").exists() and ask.opened == []     # 폴더도 탐색기도 열지 않는다


# ── ask_notebooklm ──

def test_notebooklm_prompt_points_at_the_lesson_heading(ask, monkeypatch):
    monkeypatch.setattr(app, "registry_notebook", lambda topic: "")
    cfg = {"subjects": {"수학": {"notebooklm": "https://notebooklm.google.com/notebook/abc"}}}
    result = app.ask_notebooklm(cfg, "수학", "3. 분수", "3(3~4)", "분수의 덧셈")
    assert result["url"] == "https://notebooklm.google.com/notebook/abc"
    assert "3~4차시" in result["prompt"] and "분수의 덧셈" in result["prompt"]
    assert "Ctrl+V" in result["message"] and "첫 화면" not in result["message"]


def test_notebooklm_without_url_in_config_or_registry_opens_the_start_page(ask, monkeypatch):
    monkeypatch.setattr(app, "registry_notebook", lambda topic: "")
    result = app.ask_notebooklm({}, "수학", "3. 분수", "2", "덧셈")
    assert result["url"] is None and "첫 화면" in result["message"]


def test_notebooklm_uses_registry_when_config_has_no_url(ask, monkeypatch):
    seen = []
    monkeypatch.setattr(app, "registry_notebook", lambda topic: (seen.append(topic), "https://notebooklm.google.com/notebook/zzz")[1])
    assert app.ask_notebooklm({}, "수학", "3. 분수", "2", "덧셈")["url"].endswith("/zzz") and seen == ["수업-수학"]


def test_notebooklm_without_unit_or_lesson_number_skips_the_heading_hint(ask, monkeypatch):
    monkeypatch.setattr(app, "registry_notebook", lambda topic: "")
    prompt = app.ask_notebooklm({}, "수학", "", "", "덧셈")["prompt"]
    assert "이번 차시: 「덧셈」" in prompt and "제목 아래" not in prompt
