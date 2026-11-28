"""day_split.py (T116): 가짜 녹음 조각·가짜 세션 기록만 쓴다. 실제 녹음·마이크·네트워크는 쓰지 않는다."""
import json
import os
import pathlib
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import day_split as ds  # noqa: E402

DAY = date(2026, 11, 30)
KST = timezone(timedelta(hours=9))
PERIODS = json.loads((ds.SKILL_DIR / "config.example.json").read_text(encoding="utf-8-sig"))["periods"]


def at(text):
    return ds.clock(DAY, text)


def piece(name, seconds):
    return {"file": name, "start": ds.piece_start(DAY, name), "seconds": seconds}


def half_hours(first="08:30", count=16):
    """30분 조각을 빈틈 없이."""
    start = at(first)
    return [piece(f"{start + timedelta(minutes=30 * i):%H%M%S}.webm", 1800) for i in range(count)]


def rec(period, start, end=None):
    return {"period": period, "start": at(start), "end": at(end) if end else None}


def split(records=(), pieces=None, **kwargs):
    return ds.split_day(DAY, half_hours() if pieces is None else pieces, kwargs.pop("periods", PERIODS),
                        list(records), **kwargs)


def table(result):
    return [(s["종류"], s["시작"][:5], s["끝"][:5], s["근거"]) for s in result["구간"]]


def seg(result, kind):
    return next(s for s in result["구간"] if s["종류"] == kind)


def noted(result, word):
    return any(word in note for note in result["알림"])


# ── 기본 표 ──

def test_timetable_only_day_is_all_guessed_with_lunch():
    result = split()
    assert table(result)[:4] == [("수업 전", "08:30", "09:00", "추정"), ("교시1", "09:00", "09:40", "추정"),
                                 ("쉬는 시간", "09:40", "09:50", "추정"), ("교시2", "09:50", "10:30", "추정")]
    assert [s["종류"] for s in result["구간"]].count("점심") == 1
    assert ("점심", "12:20", "13:20", "추정") in table(result)
    assert table(result)[-1] == ("방과 후", "14:50", "16:30", "추정")
    assert noted(result, "시간표 전체")


def test_segments_are_continuous_and_do_not_overlap():
    result = split([rec(1, "09:03", "09:47"), rec(3, "10:40", "11:33")])
    rows = result["구간"]
    assert all(a["끝"] == b["시작"] for a, b in zip(rows, rows[1:]))


def test_period_across_two_pieces_has_offsets_in_each():
    result = split()
    assert seg(result, "교시1")["조각"] == [{"파일": "090000.webm", "시작초": 0, "끝초": 1800},
                                            {"파일": "093000.webm", "시작초": 0, "끝초": 600}]
    assert seg(result, "교시1")["빈초"] == 0
    assert seg(result, "교시2")["조각"][0] == {"파일": "093000.webm", "시작초": 1200, "끝초": 1800}


# ── 기록이 먼저 ──

def test_recorded_times_come_before_the_timetable():
    result = split([rec(1, "09:04", "09:42")])
    assert table(result)[:3] == [("수업 전", "08:30", "09:04", "기록"), ("교시1", "09:04", "09:42", "기록"),
                                 ("쉬는 시간", "09:42", "09:50", "추정")]


def test_gap_between_two_recorded_lessons_is_recorded():
    result = split([rec(1, "09:00", "09:41"), rec(2, "09:52", "10:30")])
    assert ("쉬는 시간", "09:41", "09:52", "기록") in table(result)


def test_lesson_ending_later_than_timetable_pushes_the_next_guessed_one():
    result = split([rec(1, "09:00", "09:55")])
    assert ("교시1", "09:00", "09:55", "기록") in table(result)
    assert ("교시2", "09:55", "10:30", "추정") in table(result)
    assert table(result)[2][0] == "교시2"  # 길이 0 인 쉬는 시간은 만들지 않는다


def test_early_record_trims_the_previous_guessed_lesson():
    result = split([rec(2, "09:30", "10:30")])
    assert ("교시1", "09:00", "09:30", "추정") in table(result)


def test_missing_end_uses_timetable_and_is_marked_guessed():
    assert ("교시1", "09:05", "09:40", "추정") in table(split([rec(1, "09:05")]))


def test_missing_end_after_timetable_end_keeps_a_lesson_length():
    assert ("교시1", "09:45", "10:25", "추정") in table(split([rec(1, "09:45")]))


def test_two_recorded_lessons_overlapping_are_cut_at_the_later_start():
    result = split([rec(1, "09:00", "10:00"), rec(2, "09:50", "10:30")])
    assert ("교시1", "09:00", "09:50", "추정") in table(result)
    assert ("교시2", "09:50", "10:30", "기록") in table(result)
    assert noted(result, "겹쳐")


def test_restarted_lesson_is_one_segment():
    assert ("교시1", "09:00", "09:40", "기록") in table(split([rec(1, "09:00", "09:10"), rec(1, "09:15", "09:40")]))


def test_quick_misclick_is_ignored():
    result = split([{"period": 1, "start": at("09:01"), "end": at("09:01") + timedelta(seconds=20)}])
    assert ("교시1", "09:00", "09:40", "추정") in table(result)
    assert noted(result, "누르기 실수")


def test_record_far_from_the_timetable_is_not_used():
    result = split([rec(1, "15:30", "16:00")])
    assert ("교시1", "09:00", "09:40", "추정") in table(result)
    assert noted(result, "1시간 넘게 달라")


def test_forgotten_end_pressed_hours_later_is_not_used():
    result = split([rec(1, "09:00", "13:00")])
    assert ("교시1", "09:00", "09:40", "추정") in table(result)
    assert noted(result, "'수업 마침'")


def test_record_for_a_period_not_in_the_timetable_is_kept():
    result = split([rec(7, "15:00", "15:40")])
    assert ("교시7", "15:00", "15:40", "기록") in table(result)


# ── 그날 교시 수·점심 ──

def test_short_day_with_last_period_makes_the_rest_after_school():
    result = split(last_period=4)
    assert table(result)[-1] == ("방과 후", "12:20", "16:30", "추정")
    assert not any(s["종류"] in ("교시5", "교시6", "점심") for s in result["구간"])


def test_record_beyond_last_period_still_counts():
    kinds = [s["종류"] for s in split([rec(5, "13:20", "14:00")], last_period=4)["구간"]]
    assert "교시5" in kinds and "점심" in kinds and "교시6" not in kinds


def test_record_beyond_last_period_brings_the_periods_before_it():
    result = split([rec(6, "14:15")], last_period=4)
    assert ("교시5", "13:20", "14:00", "추정") in table(result)
    assert ("교시6", "14:15", "14:50", "추정") in table(result)


@pytest.mark.parametrize("stray", [rec(6, "20:00", "20:30"), rec(6, "14:10", "14:10")])
def test_unusable_record_does_not_lengthen_a_short_day(stray):
    result = split([stray], last_period=4)
    assert not any(s["종류"] in ("교시5", "교시6") for s in result["구간"])
    assert table(result)[-1][:2] == ("방과 후", "12:20")
    assert len(result["알림"]) == 2  # '몇 교시까지' 안내 + 그 기록을 안 쓴 까닭


def test_fix_file_day_accepts_a_record_for_an_unlisted_period_at_any_time():
    result = split([rec(5, "10:20", "10:50")], fix={"periods": [{"no": 1, "start": "09:00", "end": "09:30"}]})
    assert ("교시5", "10:20", "10:50", "기록") in table(result)


def test_fix_file_periods_replace_the_timetable():
    fix = {"periods": [{"no": 1, "start": "09:00", "end": "09:30"}, {"no": 2, "start": "09:35", "end": "10:05"}]}
    result = split(fix=fix, last_period=6)
    assert result["시간표"] == "고침 파일"
    assert [t[:3] for t in table(result)[1:]] == [("교시1", "09:00", "09:30"), ("쉬는 시간", "09:30", "09:35"),
                                                 ("교시2", "09:35", "10:05"), ("방과 후", "10:05", "16:30")]


def test_fix_file_can_move_lunch():
    result = split(fix={"lunch": {"start": "11:30", "end": "11:40"}})
    assert ("점심", "11:30", "11:40", "추정") in table(result)
    assert ("쉬는 시간", "12:20", "13:20", "추정") in table(result)


@pytest.mark.parametrize("fix", [[], {"periods": "1교시"}, {"periods": [{"no": 1, "start": "9시", "end": "10:00"}]},
                                 {"periods": [{"no": 1, "start": "10:00", "end": "09:00"}]},
                                 {"lunch": {"start": "12:00"}}])
def test_broken_fix_file_is_an_error_not_silently_ignored(fix):
    with pytest.raises(ds.SplitError):
        split(fix=fix)


# ── 녹음이 빈 시간 ──

def test_missing_recording_time_is_counted():
    result = split(pieces=[piece("090000.webm", 600), piece("092000.webm", 600)])
    first = seg(result, "교시1")
    assert first["빈초"] == 2400 - 1200
    assert [p["파일"] for p in first["조각"]] == ["090000.webm", "092000.webm"]
    assert seg(result, "교시3")["조각"] == [] and seg(result, "교시3")["빈초"] == 2400
    assert not any(s["종류"] in ("수업 전", "방과 후") for s in result["구간"])


def test_overlapping_pieces_are_not_counted_twice():
    result = split(pieces=[piece("090000.webm", 1800), piece("091000.webm", 600)])
    assert seg(result, "교시1")["빈초"] == 600


def test_no_recording_still_lists_the_lessons():
    result = split(pieces=[])
    assert [s["종류"] for s in result["구간"]][:2] == ["교시1", "교시2"]
    assert noted(result, "녹음 조각이 없어요")


def test_recording_past_midnight_stops_at_midnight():
    last = seg(split(pieces=[piece("233000.webm", 3600)]), "방과 후")
    assert last["끝"] == "24:00:00"
    assert last["길이초"] == (24 * 60 - (14 * 60 + 50)) * 60 and last["빈초"] == last["길이초"] - 1800


# ── 파일 이름·세션 기록 ──

def test_piece_names():
    assert ds.piece_start(DAY, "083005.webm") == datetime(2026, 11, 30, 8, 30, 5)
    assert ds.piece_start(DAY, "083005_2.m4a") == datetime(2026, 11, 30, 8, 30, 5)
    for bad in ("083005.txt", "0830.webm", "256000.webm", "1교시_수학.webm", "0830051.webm"):
        assert ds.piece_start(DAY, bad) is None


def memo(hhmm_kst, text, **extra):
    stamp = datetime.combine(DAY, at(hhmm_kst).time(), KST).astimezone(timezone.utc)
    return {"kind": "sys", "text": text, "at": stamp.isoformat().replace("+00:00", "Z"), **extra}


def test_session_records_use_local_time_and_only_that_day():
    session = {"period": 2, "memos": [
        memo("09:50", "수업 시작"), {"kind": "note", "text": "수업 시작", "at": "2026-11-30T01:00:00Z"},
        memo("10:30", "수업 마침"), memo("10:40", "수업 시작", period=3),
        {"kind": "sys", "text": "수업 시작", "at": "2026-12-02T01:00:00Z"}, "깨진 줄",
    ]}
    got = ds.session_records(DAY, session, tz=KST)
    assert got == [{"period": 2, "start": at("09:50"), "end": at("10:30")},
                   {"period": 3, "start": at("10:40"), "end": None}]
    assert ds.session_records(DAY, None) == [] and ds.session_records(DAY, {"memos": "x"}) == []


# ── 파일 읽기·쓰기 ──

def make_data(tmp_path):
    audio = tmp_path / "day_audio" / DAY.isoformat()
    audio.mkdir(parents=True)
    for name in ("090000.webm", "093000.webm", "memo.txt"):
        (audio / name).write_bytes(b"fake")
    sessions = tmp_path / "sessions" / DAY.isoformat()
    sessions.mkdir(parents=True)
    session = {"memos": [memo("09:02", "수업 시작"), {"kind": "note", "text": "학생A 질문", "at": "2026-11-30T00:10:00Z"},
                         memo("09:41", "수업 마침")]}
    (sessions / "1교시_수학.json").write_text(json.dumps(session, ensure_ascii=False), encoding="utf-8")
    other = {"memos": [memo("13:25", "수업 시작", period=5), memo("14:00", "수업 마침")]}  # 받아쓴 글 파일은 읽지 않는다
    (sessions / "1교시_수학.transcript.json").write_text(json.dumps(other, ensure_ascii=False), encoding="utf-8")
    return audio


def test_run_writes_table_without_memo_text_and_keeps_recordings(tmp_path):
    audio = make_data(tmp_path)
    before = sorted((p.name, p.read_bytes()) for p in audio.iterdir())
    result, target = ds.run(DAY, tmp_path, {"periods": PERIODS}, length=lambda path: 1800.0, tz=KST)
    assert target == tmp_path / "day_split" / "2026-11-30.json"
    assert json.loads(target.read_text(encoding="utf-8")) == result
    assert ("교시1", "09:02", "09:41", "기록") in table(result)
    assert not any(row[0] == "교시5" and row[3] == "기록" for row in table(result))
    assert not any(row[:2] == ("교시5", "13:25") for row in table(result))
    text = target.with_suffix(".md").read_text(encoding="utf-8")
    assert "| 1교시 | 09:02 | 09:41 | 기록 |" in text and "090000.webm 02:00~30:00" in text
    assert "학생A" not in text and "학생A" not in target.read_text(encoding="utf-8")
    assert sorted((p.name, p.read_bytes()) for p in audio.iterdir()) == before


def test_run_reads_the_fix_file_and_never_overwrites_it(tmp_path):
    make_data(tmp_path)
    fix = tmp_path / "day_split" / "2026-11-30.fix.json"
    fix.parent.mkdir()
    body = '{"periods": [{"no": 1, "start": "09:00", "end": "09:30"}]}'
    fix.write_text(body, encoding="utf-8-sig")  # 메모장이 BOM 을 붙여도 읽는다
    result, _ = ds.run(DAY, tmp_path, {"periods": PERIODS}, length=lambda path: 1800.0, tz=KST)
    assert result["시간표"] == "고침 파일" and fix.read_text(encoding="utf-8-sig") == body
    fix.write_text("{틀린", encoding="utf-8")
    with pytest.raises(ds.SplitError, match="fix.json"):
        ds.run(DAY, tmp_path, {"periods": PERIODS}, length=lambda path: 1800.0, tz=KST)


def test_unreadable_length_is_guessed_from_file_time_or_skipped(tmp_path):
    folder = tmp_path / "audio"
    folder.mkdir()
    good, bad = folder / "090000.webm", folder / "100000.webm"
    good.write_bytes(b"x")
    bad.write_bytes(b"x")
    os.utime(good, (at("09:10").timestamp(),) * 2)
    os.utime(bad, (at("23:00").timestamp(),) * 2)  # 4시간 넘게 뒤 → 짐작하지 않음
    notes = []
    pieces = ds.load_pieces(DAY, folder, lambda path: None, notes)
    assert [(p["file"], p["seconds"]) for p in pieces] == [("090000.webm", 600.0)]
    assert len(notes) == 2


class Ran:
    def __init__(self, *outputs):
        self.outputs, self.commands = list(outputs), []

    def __call__(self, command, **kwargs):
        self.commands.append(command)
        return subprocess.CompletedProcess(command, 1, b"", self.outputs.pop(0).encode())


def test_probe_reads_header_length_or_reads_to_the_end():
    ran = Ran("  Duration: 00:30:00.50, start: 0.0")
    assert ds.probe_seconds("ffmpeg", pathlib.Path("a.webm"), ran) == 1800.5 and len(ran.commands) == 1
    ran = Ran("  Duration: N/A", "time=00:00:10.00 x\rtime=00:12:00.25 x")
    assert ds.probe_seconds("ffmpeg", pathlib.Path("a.webm"), ran) == 720.25 and "null" in ran.commands[1]
    assert ds.probe_seconds("ffmpeg", pathlib.Path("a.webm"), Ran("깨짐", "깨짐")) is None

    def missing(command, **kwargs):
        raise OSError("없음")

    assert ds.probe_seconds("ffmpeg", pathlib.Path("a.webm"), missing) is None


@pytest.mark.parametrize("answer, expected", [(([{"period": 2}, {"period": 4}, {"period": None}], "진도표"), 4),
                                              (([], "Supabase 연결 오류"), None)])
def test_last_period_comes_from_the_schedule(monkeypatch, answer, expected):
    import assistant_server

    monkeypatch.setattr(assistant_server, "fetch_schedule", lambda cfg, day: answer)
    assert ds.scheduled_last_period(DAY, {}) == expected


def test_main_uses_the_data_folder_and_prints_only_counts(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(ds, "data_dir", lambda skill: tmp_path)
    monkeypatch.setattr(ds, "scheduled_last_period", lambda day, cfg: pytest.fail("--last 를 줬으면 묻지 않는다"))
    monkeypatch.setattr(ds.audio_export, "find_ffmpeg", lambda cfg: None)
    assert ds.main(["--date", DAY.isoformat(), "--last", "4"]) == 0
    out = capsys.readouterr().out
    assert "구간" in out and str(tmp_path / "day_split" / "2026-11-30.md") in out
    (tmp_path / "config.json").write_text("{틀린", encoding="utf-8")
    assert ds.main(["--date", DAY.isoformat(), "--last", "4"]) == 1
    assert "config.json" in capsys.readouterr().err
