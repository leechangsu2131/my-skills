"""Tests for the pure comparison/conversion helpers in sync_semester2.py."""

import importlib.util
import sys
import types
from pathlib import Path

import pytest


@pytest.fixture
def sync_module(monkeypatch):
    # The target module imports these dependencies at module load time, but
    # the tested helpers do not use them. Keep the tests offline and secret-free.
    requests_stub = types.ModuleType("requests")
    truststore_stub = types.ModuleType("truststore")
    skill_env_stub = types.ModuleType("skill_env")
    skill_env_stub.load_env = lambda: None
    monkeypatch.setitem(sys.modules, "requests", requests_stub)
    monkeypatch.setitem(sys.modules, "truststore", truststore_stub)
    monkeypatch.setitem(sys.modules, "skill_env", skill_env_stub)

    script = Path(__file__).resolve().parents[1] / "scripts" / "sync_semester2.py"
    spec = importlib.util.spec_from_file_location("sync_semester2_under_test", script)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("value", "default", "expected"),
    [
        (None, 9, 9),
        ("", 9, 9),
        ("  ", 9, 9),
        (" 12 ", None, 12),
        pytest.param(12.0, None, 12, marks=pytest.mark.xfail(reason="ISSUE: safe_int(12.0) 이 None — int(\"12.0\") 실패", strict=True)),
        ("not-a-number", 9, 9),
        ([], 9, 9),
    ],
)
def test_safe_int(value, default, expected, sync_module):
    assert sync_module.safe_int(value, default) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, ""),
        ("  수학  ", "수학"),
        (0, ""),
        ("", ""),
    ],
)
def test_clean(value, expected, sync_module):
    assert sync_module.clean(value) == expected


def test_make_slot_key_normalizes_values_and_defaults_order(sync_module):
    slot = {
        "slot_date": " 2026-09-03 ",
        "slot_period": " 4 ",
        "slot_order": "",
    }

    assert sync_module.make_slot_key(" lesson-1 ", slot) == (
        " lesson-1 ",
        "2026-09-03",
        4,
        1,
    )


def test_make_slot_key_keeps_missing_period_as_none(sync_module):
    assert sync_module.make_slot_key("L2", {"slot_date": None}) == (
        "L2",
        "",
        None,
        1,
    )


def test_lesson_payload_converts_schedule_row(sync_module):
    row = {
        "lesson_id": " L-001 ",
        "차시": " 3 ",
        "수업내용": "  분수의 덧셈 ",
        "pdf파일": " unit.pdf ",
        "시작페이지": "10",
        "끝페이지": "12",
        "비고": "  복습 ",
        "연장횟수": "2",
        "_row": "18",
    }

    assert sync_module.lesson_payload(row, "subject-id", "unit-id") == {
        "legacy_lesson_id": "L-001",
        "subject_id": "subject-id",
        "unit_id": "unit-id",
        "lesson_number": 3,
        "title": "분수의 덧셈",
        "pdf_path": "unit.pdf",
        "start_page": 10,
        "end_page": 12,
        "note": "복습",
        "extension_count": 2,
        "sort_order": 18,
    }


def test_lesson_payload_uses_nulls_and_numeric_defaults(sync_module):
    assert sync_module.lesson_payload({}, "subject-id", None) == {
        "legacy_lesson_id": None,
        "subject_id": "subject-id",
        "unit_id": None,
        "lesson_number": None,
        "title": None,
        "pdf_path": None,
        "start_page": None,
        "end_page": None,
        "note": None,
        "extension_count": 0,
        "sort_order": 0,
    }


def _fake_schedule(monkeypatch, records, bridge_rows):
    schedule = types.ModuleType("schedule")
    schedule.validate_config = lambda: None
    schedule.connect = lambda: object()
    schedule.load_all = lambda _ws: records
    schedule.load_bridge_rows_for_progress_ws = lambda _ws: bridge_rows
    monkeypatch.setitem(sys.modules, "schedule", schedule)


def test_load_source_keeps_slots_on_or_after_start_date_and_skips_bad_dates(
    monkeypatch, sync_module
):
    records = [
        {"lesson_id": "L1", "수업내용": "첫 차시"},
        {"lesson_id": "L2", "수업내용": "둘째 차시"},
    ]
    bridge_rows = [
        {"lesson_id": "L1", "slot_date": "2026-07-31"},
        {"lesson_id": "L1", "slot_date": "2026-08-01"},
        {"lesson_id": "L2", "slot_date": "2026-09-02"},
        {"lesson_id": "L2", "slot_date": "잘못된 날짜"},
        {"lesson_id": "L2", "slot_date": ""},
    ]
    _fake_schedule(monkeypatch, records, bridge_rows)

    by_id, slots = sync_module.load_source(sync_module.date(2026, 8, 1))

    assert set(by_id) == {"L1", "L2"}
    assert [slot["slot_date"] for slot in slots] == ["2026-08-01", "2026-09-02"]


def test_load_source_rejects_duplicate_lesson_ids(monkeypatch, sync_module):
    records = [
        {"lesson_id": "L1", "수업내용": "첫 행"},
        {"lesson_id": "L1", "수업내용": "중복 행"},
    ]
    _fake_schedule(monkeypatch, records, [])

    with pytest.raises(ValueError, match="lesson_id 중복"):
        sync_module.load_source(sync_module.date(2026, 8, 1))


def test_load_source_rejects_slots_without_a_source_lesson(monkeypatch, sync_module):
    _fake_schedule(
        monkeypatch,
        [{"lesson_id": "L1"}],
        [{"lesson_id": "MISSING", "slot_date": "2026-08-03"}],
    )

    with pytest.raises(ValueError, match="진도표 행을 찾을 수 없음"):
        sync_module.load_source(sync_module.date(2026, 8, 1))
