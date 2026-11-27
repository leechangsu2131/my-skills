"""지난 미완료 차시 알림(T98, ISSUE-043) 시험 — 가짜 Supabase 슬롯 조회로 돈다(네트워크·데이터 폴더 안 씀).

① `supabase_schedule.overdue()` 가 오늘 앞 날짜의 planned 슬롯만, 중복 없이, 읽기만 하며 돌려주는지
② `assistant_server.state()` 의 `overdue` 목록(오늘 교시에 이미 있는 차시 제외, 오류 시 빈 목록, 다른 백엔드는 빈 목록)
"""
import json
import pathlib
import sys
from datetime import date

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import assistant_server as app  # noqa: E402
import supabase_schedule as sm  # noqa: E402

TODAY = date(2026, 11, 25)


def slot(slot_id, day, period, status, key, number, subject="국어", unit="3.5 매체", title=None, order=1):
    return {"id": slot_id, "slot_date": day, "slot_period": period, "slot_order": order, "status": status,
            "source": "", "lesson": {"legacy_lesson_id": key, "lesson_number": number, "title": title or f"{number}차시",
                                     "sort_order": number, "pdf_path": "",
                                     "subject": {"name": subject}, "unit": {"name": unit}}}


def in_range(slot_date, value):
    """'(slot_date.gte.A,slot_date.lt.B)' 의 연산자(gte·gt·lt·lte)를 그대로 지켜 판단한다."""
    ops = {"gte": lambda a, b: a >= b, "gt": lambda a, b: a > b, "lt": lambda a, b: a < b, "lte": lambda a, b: a <= b}
    for part in value.strip("()").split(","):
        _, op, bound = part.split(".", 2)
        if not ops[op](slot_date, bound):
            return False
    return True


@pytest.fixture
def fake_db(monkeypatch):
    """PostgREST 조회를 흉내: and=(slot_date.gte…,slot_date.lt…)·slot_date=eq.·status=eq. 조건만 지킨다. 쓰기는 막는다."""
    calls = {"get": [], "writes": 0}
    slots = []

    def fake_get(table, **params):
        calls["get"].append(params)
        assert table == sm.SLOTS
        rows = list(slots)
        if "and" in params:
            rows = [s for s in rows if in_range(s["slot_date"], params["and"])]
        if "slot_date" in params:
            rows = [s for s in rows if s["slot_date"] == params["slot_date"].removeprefix("eq.")]
        if "status" in params:
            rows = [s for s in rows if s["status"] == params["status"].removeprefix("eq.")]
        return sorted(rows, key=lambda s: (s["slot_date"], s["slot_period"], s["slot_order"]))

    def no_write(*args, **kwargs):
        calls["writes"] += 1
        raise AssertionError("지난 미완료 차시를 읽다가 DB 를 바꾸려 함")

    monkeypatch.setattr(sm, "_get", fake_get)
    for name in ("_patch", "_post", "_delete"):
        if hasattr(sm, name):
            monkeypatch.setattr(sm, name, no_write)
    return slots, calls


# ── supabase_schedule.overdue ──

def test_returns_only_planned_slots_before_today(fake_db):
    slots, _ = fake_db
    slots += [
        slot("a", "2026-11-24", 3, "planned", "lesson-0410", 5),
        slot("b", "2026-11-24", 4, "completed", "lesson-0300", 3),
        slot("c", "2026-11-25", 1, "planned", "lesson-0411", 6),     # 오늘은 제외
        slot("d", "2026-11-26", 1, "planned", "lesson-0412", 7),     # 내일은 제외
    ]
    rows = sm.overdue(TODAY)
    assert [(r["record_key"], r["planned_date"], r["period"]) for r in rows] == [("lesson-0410", "2026-11-24", 3)]
    assert rows[0] == {"period": 3, "subject": "국어", "unit": "3.5 매체", "lesson": "5", "title": "5차시",
                       "record_key": "lesson-0410", "slot_id": "a", "planned_date": "2026-11-24"}


def test_window_is_limited_to_days_back(fake_db):
    slots, _ = fake_db
    slots += [slot("old", "2026-10-01", 1, "planned", "lesson-0001", 1),
              slot("edge", "2026-11-11", 1, "planned", "lesson-0002", 2),     # 오늘 -14일
              slot("late", "2026-11-10", 1, "planned", "lesson-0003", 3)]
    assert [r["record_key"] for r in sm.overdue(TODAY)] == ["lesson-0002"]
    assert {r["record_key"] for r in sm.overdue(TODAY, days_back=60)} == {"lesson-0001", "lesson-0002", "lesson-0003"}


def test_same_lesson_in_several_slots_keeps_the_latest_one(fake_db):
    slots, _ = fake_db
    slots += [slot("s1", "2026-11-20", 2, "planned", "lesson-0410", 5),
              slot("s2", "2026-11-24", 3, "planned", "lesson-0410", 5)]
    rows = sm.overdue(TODAY)
    assert [(r["slot_id"], r["planned_date"]) for r in rows] == [("s2", "2026-11-24")]


def test_sorted_oldest_first_and_other_subjects_are_kept(fake_db):
    slots, _ = fake_db
    slots += [slot("m", "2026-11-24", 2, "planned", "math-0007", 7, subject="수학", unit="2. 곱셈"),
              slot("k", "2026-11-23", 5, "planned", "lesson-0409", 4)]
    assert [(r["planned_date"], r["subject"]) for r in sm.overdue(TODAY)] == [("2026-11-23", "국어"), ("2026-11-24", "수학")]


def test_slots_without_lesson_or_key_are_skipped(fake_db):
    slots, _ = fake_db
    broken = slot("x", "2026-11-24", 1, "planned", "", 1)
    nolesson = {"id": "y", "slot_date": "2026-11-24", "slot_period": 2, "slot_order": 1, "status": "planned", "lesson": None}
    slots += [broken, nolesson, slot("ok", "2026-11-24", 3, "planned", "lesson-0410", 5)]
    assert [r["record_key"] for r in sm.overdue(TODAY)] == ["lesson-0410"]


def test_limit_keeps_the_most_recent_items(fake_db, monkeypatch):
    slots, _ = fake_db
    monkeypatch.setattr(sm, "OVERDUE_LIMIT", 2)
    slots += [slot(f"s{n}", f"2026-11-{14 + n:02d}", 1, "planned", f"lesson-{n:04d}", n) for n in range(1, 5)]
    assert [r["record_key"] for r in sm.overdue(TODAY)] == ["lesson-0003", "lesson-0004"]


def test_overdue_only_reads(fake_db):
    slots, calls = fake_db
    slots.append(slot("a", "2026-11-24", 3, "planned", "lesson-0410", 5))
    sm.overdue(TODAY)
    assert calls["writes"] == 0 and len(calls["get"]) == 1
    assert calls["get"][0]["status"] == "eq.planned"          # 걸러내기는 DB 쪽에서도 한다(가져오는 양을 줄임)
    assert calls["get"][0]["and"] == "(slot_date.gte.2026-11-11,slot_date.lt.2026-11-25)"


# ── assistant_server.state / fetch_overdue ──

@pytest.fixture
def isolated_state(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "load_config", lambda: {"subjects": {"국어": {"publisher": "가출판"}}})
    monkeypatch.setattr(app, "CAUTIONS_PATH", tmp_path / "cautions.json")
    monkeypatch.setattr(app, "find_flow", lambda lesson: None)
    monkeypatch.setattr(app, "find_unit", lambda lesson: None)
    monkeypatch.setattr(app, "recent_memos", lambda subject: [])
    monkeypatch.setattr(app, "session_path", lambda day, period, subject, record_key="": tmp_path / "없는기록.json")


def test_state_lists_yesterdays_unfinished_lesson(fake_db, isolated_state):
    slots, _ = fake_db
    slots += [slot("s-yesterday", "2026-11-24", 3, "planned", "lesson-0410", 5, title="실천하기"),
              slot("s-today", "2026-11-25", 1, "completed", "lesson-0409", 4)]
    state = app.state(TODAY)
    assert [(o["record_key"], o["subject"], o["lesson"], o["planned_date"], o["period"]) for o in state["overdue"]] == \
        [("lesson-0410", "국어", "5", "2026-11-24", 3)]
    assert "lesson-0410" not in json.dumps(state["lessons"], ensure_ascii=False)   # 오늘 교시는 그대로(자동 이월 안 함)


def test_state_leaves_out_lessons_already_on_todays_periods(fake_db, isolated_state):
    slots, _ = fake_db
    slots += [slot("s-yesterday", "2026-11-24", 3, "planned", "lesson-0410", 5),
              slot("s-today", "2026-11-25", 1, "planned", "lesson-0410", 5)]
    assert app.state(TODAY)["overdue"] == []


def test_state_overdue_empty_when_nothing_is_late(fake_db, isolated_state):
    slots, _ = fake_db
    slots.append(slot("s-today", "2026-11-25", 1, "planned", "lesson-0410", 5))
    assert app.state(TODAY)["overdue"] == []


def test_failure_reading_overdue_does_not_break_state(fake_db, isolated_state, monkeypatch, capsys):
    slots, _ = fake_db
    slots.append(slot("s-today", "2026-11-25", 1, "planned", "lesson-0410", 5))
    monkeypatch.setattr(sm, "overdue", lambda day: (_ for _ in ()).throw(RuntimeError("Supabase 조회 실패 (500)")))
    state = app.state(TODAY)
    assert state["overdue"] == [] and len(state["lessons"]) == 1
    assert "지난 미완료 차시 조회 실패" in capsys.readouterr().err


def test_other_backend_has_no_overdue_list(fake_db, monkeypatch):
    called = []
    monkeypatch.setattr(sm, "overdue", lambda day: called.append(day) or [])
    assert app.fetch_overdue({"schedule_backend": "legacy"}, TODAY, []) == []
    assert called == []
