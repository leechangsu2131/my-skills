"""수업 기록 파일 처리 시험 (S1, ISSUE-046 에서 고친 동작을 지키는 시험).

    python -m pytest tests/test_session_records.py -v      (teacherlesson-assistant 폴더에서)

다루는 것: safe_name · session_path · session_matches_lesson · saved_mismatch_info · save_session ·
app.state() 가 기록을 현재 차시에 붙이거나(`saved`) 이전 기록으로 알리는(`saved_mismatch`) 규칙.
진짜 내 문서·Supabase 는 쓰지 않는다: SESSIONS·DATA 는 임시 폴더, 일정은 가짜. 소스는 고치지 않는다.
"""
import json
import pathlib
import sys
from datetime import date

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import assistant_server as app  # noqa: E402

DAY = date(2026, 11, 25)


@pytest.fixture
def sessions(tmp_path, monkeypatch):
    root = tmp_path / "data" / "sessions"
    monkeypatch.setattr(app, "DATA", tmp_path / "data")
    monkeypatch.setattr(app, "SESSIONS", root)
    return root


def write(path: pathlib.Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


# ── safe_name ──

@pytest.mark.parametrize("raw,want", [
    ("사회", "사회"),
    ("국어 활동", "국어_활동"),
    ('a/b\\c:d*e?f"g<h>i|j', "a_b_c_d_e_f_g_h_i_j"),
    ("  앞뒤  ", "앞뒤"),
    ("", "x"),
    ("///", "x"),
    (None, "None"),
])
def test_safe_name(raw, want):
    assert app.safe_name(raw) == want


def test_safe_name_is_cut_to_80_chars():
    assert len(app.safe_name("가" * 200)) == 80


# ── session_path ──

def test_session_path_without_record_key_is_old_style(sessions):
    assert app.session_path("2026-11-25", 3, "사회") == sessions / "2026-11-25" / "3교시_사회.json"


def test_session_path_with_record_key_adds_lesson_suffix(sessions):
    path = app.session_path("2026-11-25", 3, "사회", "lesson-0554")
    assert path == sessions / "2026-11-25" / "3교시_사회_lesson-0554.json"
    assert path != app.session_path("2026-11-25", 3, "사회", "lesson-0553")  # 차시가 다르면 파일도 다름


@pytest.mark.parametrize("period,no", [("3", 3), (3, 3), (None, 0), ("", 0), ("가", 0), (0, 0)])
def test_session_path_period_is_normalized(sessions, period, no):
    assert app.session_path("2026-11-25", period, "사회").name == f"{no}교시_사회.json"


def test_session_path_subject_and_key_are_made_file_safe(sessions):
    path = app.session_path("2026-11-25", 1, "국어/활동", "a:b")
    assert path.name == "1교시_국어_활동_a_b.json"


def test_session_path_rejects_escaping_the_sessions_folder(sessions):
    with pytest.raises(ValueError):
        app.session_path("../../밖", 1, "사회")


# ── session_matches_lesson ──

def lesson(**over):
    base = {"period": 3, "subject": "사회", "record_key": "lesson-0554"}
    base.update(over)
    return base


def saved(**over):
    base = {"date": "2026-11-25", "period": 3, "subject": "사회", "record_key": "lesson-0554"}
    base.update(over)
    return base


def test_matching_record_is_accepted():
    assert app.session_matches_lesson(saved(), DAY, lesson())


@pytest.mark.parametrize("field,value", [
    ("date", "2026-11-24"), ("period", 4), ("subject", "국어"), ("record_key", "lesson-0553"),
])
def test_record_with_a_different_value_is_rejected(field, value):
    assert not app.session_matches_lesson(saved(**{field: value}), DAY, lesson())


@pytest.mark.parametrize("field", ["date", "period", "subject", "record_key"])
@pytest.mark.parametrize("blank", [None, ""])
def test_old_record_missing_a_field_is_trusted(field, blank):
    assert app.session_matches_lesson(saved(**{field: blank}), DAY, lesson())
    record = saved()
    del record[field]
    assert app.session_matches_lesson(record, DAY, lesson())


def test_blank_expectation_on_the_lesson_side_is_not_compared():
    assert app.session_matches_lesson(saved(record_key="lesson-0553"), DAY, lesson(record_key=""))


def test_period_is_compared_as_a_number_so_text_forms_match():
    assert app.session_matches_lesson(saved(period="3교시"), DAY, lesson(period=3))
    assert app.session_matches_lesson(saved(period=3), DAY, lesson(period="3"))
    assert not app.session_matches_lesson(saved(period="4교시"), DAY, lesson(period=3))


@pytest.mark.parametrize("value", [None, [], "글", 3])
def test_non_dict_record_is_rejected(value):
    assert not app.session_matches_lesson(value, DAY, lesson())


def test_saved_mismatch_info_keeps_only_three_fields():
    info = app.saved_mismatch_info({"record_key": "lesson-0553", "lesson": "13차시", "title": "옛 수업", "memos": ["숨김"]})
    assert info == {"record_key": "lesson-0553", "lesson": "13차시", "title": "옛 수업"}
    assert app.saved_mismatch_info(None) == {"record_key": "", "lesson": "", "title": ""}
    assert app.saved_mismatch_info({}) == {"record_key": "", "lesson": "", "title": ""}


# ── save_session ──

def test_save_session_writes_a_file_per_lesson_and_stamps_time(sessions):
    body = {"date": "2026-11-25", "period": 3, "subject": "사회", "record_key": "lesson-0554", "memos": []}
    result = app.save_session(dict(body))
    assert result["status"] == "success"
    path = sessions / "2026-11-25" / "3교시_사회_lesson-0554.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["record_key"] == "lesson-0554"
    assert data["saved_at"].startswith("20")  # 저장 시각이 붙음
    assert not list(path.parent.glob("*.tmp"))


def test_save_session_of_another_lesson_does_not_overwrite(sessions):
    base = {"date": "2026-11-25", "period": 3, "subject": "사회", "memos": []}
    app.save_session({**base, "record_key": "lesson-0553", "title": "13"})
    app.save_session({**base, "record_key": "lesson-0554", "title": "14"})
    files = sorted(p.name for p in (sessions / "2026-11-25").glob("*.json"))
    assert files == ["3교시_사회_lesson-0553.json", "3교시_사회_lesson-0554.json"]


def test_save_session_rejects_bad_date_and_writes_nothing(sessions):
    with pytest.raises(ValueError):
        app.save_session({"date": "11월 25일", "period": 3, "subject": "사회"})
    assert not sessions.exists()


# ── state(): 기록을 현재 차시에 붙이거나 이전 기록으로 알리기 ──

def make_lesson(**over):
    base = {"period": 3, "subject": "사회", "record_key": "lesson-0554", "lesson": "14차시", "title": "오늘"}
    base.update(over)
    return base


@pytest.fixture
def state_env(sessions, tmp_path, monkeypatch):
    holder = {"lessons": [make_lesson()]}
    monkeypatch.setattr(app, "load_config", lambda: {"subjects": {"사회": {"publisher": "가출판"}}})
    monkeypatch.setattr(app, "fetch_schedule", lambda cfg, day: (holder["lessons"], "test"))
    monkeypatch.setattr(app, "CAUTIONS_PATH", tmp_path / "cautions.json")
    monkeypatch.setattr(app, "find_flow", lambda lesson: None)
    monkeypatch.setattr(app, "find_unit", lambda lesson: None)
    monkeypatch.setattr(app, "recent_memos", lambda subject: [])
    return holder


def only_lesson(holder):
    return app.state(DAY)["lessons"][0]


def test_state_attaches_the_record_saved_for_this_lesson(sessions, state_env):
    write(sessions / "2026-11-25" / "3교시_사회_lesson-0554.json", saved(title="오늘 기록"))
    got = only_lesson(state_env)
    assert got["saved"]["title"] == "오늘 기록"
    assert "saved_mismatch" not in got


def test_state_does_not_attach_another_lessons_old_record(sessions, state_env):
    """ISSUE-046 증상: 같은 날짜·교시·과목의 옛 파일(13차시)이 14차시 수업에 붙으면 안 된다."""
    write(sessions / "2026-11-25" / "3교시_사회.json", saved(record_key="lesson-0553", lesson="13차시", title="옛 기록"))
    got = only_lesson(state_env)
    assert "saved" not in got
    assert got["saved_mismatch"] == {"record_key": "lesson-0553", "lesson": "13차시", "title": "옛 기록"}


def test_state_still_reads_an_old_style_record_that_matches(sessions, state_env):
    write(sessions / "2026-11-25" / "3교시_사회.json", saved(title="예전 방식"))
    assert only_lesson(state_env)["saved"]["title"] == "예전 방식"


def test_state_prefers_the_lesson_file_over_the_old_style_file(sessions, state_env):
    write(sessions / "2026-11-25" / "3교시_사회.json", saved(title="옛 파일"))
    write(sessions / "2026-11-25" / "3교시_사회_lesson-0554.json", saved(title="차시 파일"))
    assert only_lesson(state_env)["saved"]["title"] == "차시 파일"


def test_state_mismatching_lesson_file_is_reported_not_attached(sessions, state_env):
    # 파일 이름은 이 차시인데 안의 차시 번호가 다르면(손으로 옮긴 파일 등) 붙이지 않는다
    write(sessions / "2026-11-25" / "3교시_사회_lesson-0554.json", saved(record_key="lesson-0553", title="잘못 놓인 기록"))
    got = only_lesson(state_env)
    assert "saved" not in got
    assert got["saved_mismatch"]["title"] == "잘못 놓인 기록"


def test_state_without_record_key_uses_the_old_style_file(sessions, state_env):
    state_env["lessons"] = [make_lesson(record_key="")]
    write(sessions / "2026-11-25" / "3교시_사회.json", saved(record_key="", title="키 없음"))
    assert only_lesson(state_env)["saved"]["title"] == "키 없음"


def test_state_without_record_key_reports_a_different_day_record(sessions, state_env):
    state_env["lessons"] = [make_lesson(record_key="")]
    write(sessions / "2026-11-25" / "3교시_사회.json", saved(date="2026-11-18", record_key="", title="지난주"))
    got = only_lesson(state_env)
    assert "saved" not in got and got["saved_mismatch"]["title"] == "지난주"


def test_state_with_no_record_has_neither_key(sessions, state_env):
    got = only_lesson(state_env)
    assert "saved" not in got and "saved_mismatch" not in got


def test_state_ignores_a_broken_record_file(sessions, state_env):
    path = sessions / "2026-11-25" / "3교시_사회_lesson-0554.json"
    path.parent.mkdir(parents=True)
    path.write_text("{깨진", encoding="utf-8")
    got = only_lesson(state_env)
    assert "saved" not in got and "saved_mismatch" not in got


def test_state_saved_round_trip_through_save_session(sessions, state_env):
    app.save_session({"date": "2026-11-25", "period": 3, "subject": "사회", "record_key": "lesson-0554",
                      "title": "저장했다 읽기", "memos": [{"kind": "note", "text": "ok"}]})
    got = only_lesson(state_env)
    assert got["saved"]["title"] == "저장했다 읽기"
    assert got["saved"]["memos"][0]["text"] == "ok"
