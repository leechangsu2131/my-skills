"""ISSUES.md 열린 항목의 재현 시험(S3). 고치지 않았고, 아직 안 고쳐진 증상은 xfail 로 표시한다.

    python -m pytest tests/test_issue_repros.py -v      (teacherlesson-assistant 폴더에서)

고치는 사람은 해당 시험의 xfail 표시를 지우고 통과시킨다(strict 라서 고쳐지면 XPASS 로 실패해 알려 준다).
진짜 Supabase·데이터 폴더는 쓰지 않는다: 슬롯 조회를 가짜로 바꾸고, 수업 흐름·기록 폴더는 임시 폴더로 돌린다.
"""
import json
import pathlib
import sys
from datetime import date

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import assistant_server as app  # noqa: E402
import supabase_schedule as sm  # noqa: E402

TODAY, YESTERDAY = date(2026, 11, 25), date(2026, 11, 24)
OVERDUE_KEY = "lesson-0410"


def slot(slot_id, day, period, status, key, number, sort_order):
    return {"id": slot_id, "slot_date": day.isoformat(), "slot_period": period, "slot_order": 1, "status": status,
            "source": "", "lesson": {"legacy_lesson_id": key, "lesson_number": number, "title": f"{number}차시",
                                     "sort_order": sort_order, "pdf_path": "",
                                     "subject": {"name": "국어"}, "unit": {"name": "3.5 매체"}}}


# ISSUE-043 실제 사례를 줄인 것: 어제 3교시 5차시가 미완료로 남고, 오늘 1교시에는 완료된 4차시가 있다.
SLOTS = [
    slot("s-yesterday", YESTERDAY, 3, "planned", OVERDUE_KEY, 5, 5),
    slot("s-today", TODAY, 1, "completed", "lesson-0409", 4, 4),
]


@pytest.fixture
def fake_supabase(monkeypatch):
    """슬롯 조회를 흉내: slot_date=eq.<날짜>, and=(slot_date.gte.A,slot_date.lt.B), status=eq.<상태> 조건을 지킨다."""
    def fake_get(table, **params):
        assert table == sm.SLOTS
        want = params.get("slot_date", "").removeprefix("eq.")
        rows = [s for s in SLOTS if not want or s["slot_date"] == want]
        if "and" in params:
            lo, hi = [part.split(".", 2)[2] for part in params["and"].strip("()").split(",")]   # gte, lt 가정
            rows = [s for s in rows if lo <= s["slot_date"] < hi]
        if "status" in params:
            rows = [s for s in rows if s["status"] == params["status"].removeprefix("eq.")]
        return rows
    monkeypatch.setattr(sm, "_get", fake_get)


@pytest.fixture
def isolated_state(tmp_path, monkeypatch, fake_supabase):
    """app.state() 가 내 문서의 흐름·기록·주의점을 읽지 않게 한다."""
    monkeypatch.setattr(app, "load_config", lambda: {"subjects": {"국어": {"publisher": "가출판"}}})
    monkeypatch.setattr(app, "CAUTIONS_PATH", tmp_path / "cautions.json")
    monkeypatch.setattr(app, "find_flow", lambda lesson: None)
    monkeypatch.setattr(app, "find_unit", lambda lesson: None)
    monkeypatch.setattr(app, "recent_memos", lambda subject: [])
    monkeypatch.setattr(app, "session_path", lambda day, period, subject, record_key="": tmp_path / "없는기록.json")


# ── ISSUE-043: 날짜 지난 미완료 차시는 자동 이월하지 않고 `overdue` 로 알린다(T98에서 구현) ──

def test_issue_043_control_fake_returns_yesterday_when_asked_for_yesterday(fake_supabase):
    """(대조) 가짜가 날짜 조건을 지키는지: 어제를 물으면 어제 미완료 차시가 나온다."""
    rows = sm.day_schedule(YESTERDAY)
    assert [(r["record_key"], r["status"]) for r in rows] == [(OVERDUE_KEY, "planned")]


def test_issue_043_control_today_shows_the_completed_lesson(fake_supabase):
    """(대조) 지금 동작: 오늘은 오늘 날짜 슬롯만 본다. 이 시험이 깨지면 ISSUE-043 의 전제가 바뀐 것이다."""
    rows = sm.day_schedule(TODAY)
    assert [(r["record_key"], r["status"]) for r in rows] == [("lesson-0409", "completed")]


def test_issue_043_today_state_reveals_overdue_planned_lesson(isolated_state):
    state = app.state(TODAY)
    assert OVERDUE_KEY in json.dumps(state, ensure_ascii=False), "어제 3교시에 미완료로 남은 5차시가 오늘 화면 정보에 없다"
