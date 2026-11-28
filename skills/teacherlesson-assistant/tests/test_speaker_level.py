"""스피커 소리 크기 기록·영상 재생 구간 찾기 시험 (T121, speaker_level.py).

    python -m pytest tests/test_speaker_level.py -v      (teacherlesson-assistant 폴더에서)

진짜 스피커·soundcard·프로세스는 쓰지 않는다. 크기 기록은 가짜 숫자, 루프백 장치는 가짜 read_block,
켜기·끄기는 가짜 spawn·kill·alive. 소스는 고치지 않는다.
"""
import math
import pathlib
import sys
from datetime import date, datetime, timedelta

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import speaker_level as sl  # noqa: E402

T0 = datetime(2026, 11, 28, 10, 0, 0)
QUIET, LOUD = -80.0, -25.0


def rows_from(pattern: str, start=T0, quiet=QUIET, loud=LOUD):
    """'.' = 조용한 1초, '#' = 소리 나는 1초, ' ' = 기록 없는 1초(PC 잠듦 등)."""
    out = []
    for i, ch in enumerate(pattern):
        if ch == " ":
            continue
        out.append((start + timedelta(seconds=i), loud if ch == "#" else quiet))
    return out


def spans(segments):
    return [(int((a - T0).total_seconds()), int((b - T0).total_seconds())) for a, b in segments]


# ── rms_db ──

def test_rms_db_of_full_scale_is_zero_and_half_is_about_minus_six():
    assert sl.rms_db([1.0, -1.0, 1.0, -1.0]) == 0.0
    assert sl.rms_db([0.5] * 100) == pytest.approx(-6.0, abs=0.1)


def test_rms_db_silence_and_empty_are_the_floor():
    assert sl.rms_db([]) == sl.FLOOR_DB
    assert sl.rms_db([0.0] * 50) == sl.FLOOR_DB
    assert sl.rms_db(iter(())) == sl.FLOOR_DB


def test_rms_db_never_goes_below_the_floor_and_is_rounded_to_one_decimal():
    assert sl.rms_db([1e-9]) == sl.FLOOR_DB
    value = sl.rms_db([0.123] * 10)
    assert value == round(value, 1) and value == pytest.approx(20 * math.log10(0.123), abs=0.05)


def test_rms_db_accepts_any_iterable_of_numbers():
    assert sl.rms_db(x for x in (0.5, 0.5)) == sl.rms_db((0.5, 0.5)) == sl.rms_db([0.5, 0.5])


# ── 기록 줄 ──

def test_row_round_trip_drops_microseconds_and_keeps_one_decimal():
    line = sl.format_row(datetime(2026, 11, 28, 10, 15, 3, 999999), -42.14)
    assert line == "2026-11-28T10:15:03,-42.1"
    assert sl.parse_rows(line) == [(datetime(2026, 11, 28, 10, 15, 3), -42.1)]


def test_parse_rows_skips_header_blank_and_broken_lines_and_sorts():
    text = "time,db\n\n2026-11-28T10:00:05,-30.0\n깨진줄\n2026-11-28T10:00:01,-50.0\n2026-11-28T10:00:09,abc\n"
    assert [r[0].second for r in sl.parse_rows(text)] == [1, 5]
    assert sl.parse_rows("") == sl.parse_rows(None) == []


# ── 영상 구간 찾기 ──

def test_no_sound_means_no_video():
    assert sl.find_video_segments(rows_from("." * 120)) == []
    assert sl.find_video_segments([]) == []


def test_short_beep_is_not_a_video():
    assert sl.find_video_segments(rows_from("." * 10 + "###" + "." * 30)) == []


def test_long_video_is_found_with_exact_start_and_end():
    segs = sl.find_video_segments(rows_from("." * 10 + "#" * 60 + "." * 10))
    assert spans(segs) == [(10, 70)]                    # 끝 = 마지막 소리 줄 + 1초


def test_short_pause_inside_a_video_is_joined():
    pattern = "#" * 30 + "." * 5 + "#" * 30                # 5초 조용 < JOIN_GAP_SECONDS(8)
    assert spans(sl.find_video_segments(rows_from(pattern))) == [(0, 65)]


def test_long_pause_splits_into_two_videos():
    pattern = "#" * 30 + "." * 30 + "#" * 30
    assert spans(sl.find_video_segments(rows_from(pattern))) == [(0, 30), (60, 90)]


def test_missing_rows_count_as_a_break_not_as_sound():
    pattern = "#" * 30 + " " * 20 + "#" * 30                # 기록 없는 20초(PC 잠듦) → 이어 붙이지 않음
    assert spans(sl.find_video_segments(rows_from(pattern))) == [(0, 30), (50, 80)]


def test_gap_exactly_at_the_join_limit_is_still_joined_and_one_over_is_not():
    limit = int(sl.JOIN_GAP_SECONDS)
    joined = "#" * 15 + "." * (limit - 1) + "#" * 15          # 소리 줄 사이가 limit 초
    split = "#" * 15 + "." * limit + "#" * 15                  # limit+1 초
    assert spans(sl.find_video_segments(rows_from(joined))) == [(0, 15 + limit - 1 + 15)]      # 한 영상으로 이어짐
    assert sl.find_video_segments(rows_from(split)) == []          # 끊겨서 15초짜리 둘 → 둘 다 너무 짧아 빠짐
    assert len(sl.find_video_segments(rows_from(split), min_seconds=10)) == 2


def test_segment_exactly_at_min_length_is_kept_and_one_second_shorter_is_dropped():
    n = int(sl.MIN_VIDEO_SECONDS)
    assert len(sl.find_video_segments(rows_from("#" * n))) == 1
    assert sl.find_video_segments(rows_from("#" * (n - 1))) == []


def test_level_exactly_at_the_threshold_is_not_loud():
    assert sl.find_video_segments([(T0 + timedelta(seconds=i), sl.LOUD_DB) for i in range(60)]) == []
    assert len(sl.find_video_segments([(T0 + timedelta(seconds=i), sl.LOUD_DB + 0.1) for i in range(60)])) == 1


def test_thresholds_can_be_overridden():
    quiet_movie = rows_from("#" * 30, loud=-60.0)
    assert sl.find_video_segments(quiet_movie) == []                          # 기본 기준(-45)보다 작은 소리
    assert len(sl.find_video_segments(quiet_movie, loud_db=-70.0)) == 1
    assert len(sl.find_video_segments(rows_from("#" * 10), min_seconds=5)) == 1


def test_unsorted_rows_give_the_same_answer():
    rows = rows_from("." * 5 + "#" * 40 + "." * 5)
    assert sl.find_video_segments(list(reversed(rows))) == sl.find_video_segments(rows)


def test_segments_text_lists_times_and_length():
    text = sl.segments_text(sl.find_video_segments(rows_from("." * 10 + "#" * 75)))
    assert text == "10:00:10 ~ 10:01:25 (1분 15초)"
    assert sl.segments_text([]) == "영상 재생 구간이 없어요."


# ── 날짜 폴더 파일 ──

def test_segments_for_day_reads_that_days_csv_only(tmp_path):
    day = tmp_path / "2026-11-28"
    day.mkdir()
    (day / sl.LEVEL_FILE).write_text("\n".join(sl.format_row(t, db) for t, db in rows_from("#" * 40)) + "\n", encoding="utf-8")
    assert len(sl.segments_for_day(tmp_path, "2026-11-28")) == 1
    assert sl.segments_for_day(tmp_path, "2026-11-27") == []                    # 다른 날은 파일이 없음 → 빈 목록


def test_level_path_is_inside_the_day_folder(tmp_path):
    assert sl.level_path(tmp_path, date(2026, 11, 28)) == tmp_path / "2026-11-28" / "speaker_level.csv"


# ── run_loop: 가짜 루프백 장치 ──

class Clock:
    def __init__(self, start):
        self.t = start

    def __call__(self):
        now = self.t
        self.t += timedelta(seconds=1)
        return now


def test_run_loop_writes_one_row_per_block_with_level_only(tmp_path):
    blocks = iter([[0.5] * 100, [0.0] * 100, [1.0, -1.0]])
    count = {"n": 0}

    def read_block():
        count["n"] += 1
        return next(blocks)

    reason = sl.run_loop(read_block, tmp_path, now=Clock(T0), should_stop=lambda: count["n"] >= 3)
    assert reason == "끔"
    lines = (tmp_path / "2026-11-28" / sl.LEVEL_FILE).read_text(encoding="utf-8").splitlines()
    assert lines == ["2026-11-28T10:00:00,-6.0", "2026-11-28T10:00:01,-100.0", "2026-11-28T10:00:02,0.0"]
    # 소리 조각이 아니라 '시각,크기' 두 칸만 — 소리는 어디에도 저장되지 않는다
    assert all(len(line.split(",")) == 2 for line in lines)
    assert [p.name for p in tmp_path.rglob("*") if p.is_file()] == [sl.LEVEL_FILE]


def test_run_loop_switches_folder_after_midnight(tmp_path):
    clock = Clock(datetime(2026, 11, 28, 23, 59, 58))
    count = {"n": 0}

    def read_block():
        count["n"] += 1
        return [0.1] * 10

    sl.run_loop(read_block, tmp_path, now=clock, should_stop=lambda: count["n"] >= 4)
    first = (tmp_path / "2026-11-28" / sl.LEVEL_FILE).read_text(encoding="utf-8").splitlines()
    second = (tmp_path / "2026-11-29" / sl.LEVEL_FILE).read_text(encoding="utf-8").splitlines()
    assert [l[:19] for l in first] == ["2026-11-28T23:59:58", "2026-11-28T23:59:59"]
    assert [l[:19] for l in second] == ["2026-11-29T00:00:00", "2026-11-29T00:00:01"]


def test_run_loop_appends_to_an_existing_file(tmp_path):
    path = sl.level_path(tmp_path, date(2026, 11, 28))
    path.parent.mkdir(parents=True)
    path.write_text("2026-11-28T09:00:00,-30.0\n", encoding="utf-8")
    sl.run_loop(lambda: [0.1], tmp_path, now=Clock(T0), should_stop=iter([False, True]).__next__)
    assert len(path.read_text(encoding="utf-8").splitlines()) == 2


def test_run_loop_survives_a_few_read_errors_and_resets_the_count(tmp_path):
    script = iter([OSError("a"), OSError("b"), [0.2], OSError("c"), OSError("d"), [0.2]])
    seen, count = [], {"n": 0}

    def read_block():
        item = next(script)
        count["n"] += 1
        if isinstance(item, Exception):
            raise item
        return item

    reason = sl.run_loop(read_block, tmp_path, now=Clock(T0), should_stop=lambda: count["n"] >= 6,
                         max_errors=3, on_error=seen.append)
    assert reason == "끔" and len(seen) == 4         # 에러가 연달아 3번이 안 되면 계속
    assert len((tmp_path / "2026-11-28" / sl.LEVEL_FILE).read_text(encoding="utf-8").splitlines()) == 2


def test_run_loop_stops_after_too_many_errors_in_a_row(tmp_path):
    calls = []

    def read_block():
        calls.append(1)
        raise OSError("장치 없음")

    reason = sl.run_loop(read_block, tmp_path, now=Clock(T0), max_errors=3)
    assert "멈췄어요" in reason and not any(tmp_path.rglob("*.csv"))
    assert len(calls) == 3                                           # 정확히 3번째 실패에서 멈춤(4번째를 시도하지 않음)


def test_end_to_end_fake_video_playing_is_found_from_the_loop(tmp_path):
    levels = [0.0005] * 30 + [0.3] * 45 + [0.0005] * 30                 # 조용 → 영상(약 -11 dB) → 조용
    it, count = iter(levels), {"n": 0}

    def read_block():
        count["n"] += 1
        return [next(it)] * 8

    sl.run_loop(read_block, tmp_path, now=Clock(T0), should_stop=lambda: count["n"] >= len(levels))
    assert spans(sl.segments_for_day(tmp_path, "2026-11-28")) == [(30, 75)]


# ── 루프백 장치 열기(soundcard 는 가짜) ──

class FakeArray(list):
    def reshape(self, *_):
        return self


class FakeRecorder:
    def __init__(self):
        self.entered, self.asked = False, []

    def __enter__(self):
        self.entered = True
        return self

    def record(self, numframes):
        self.asked.append(numframes)
        return FakeArray([0.25] * numframes)


class FakeSC:
    class _Speaker:
        name = "교실 스피커"

    def __init__(self):
        self.recorder_obj, self.mic_args, self.rec_args = FakeRecorder(), None, None

    def default_speaker(self):
        return self._Speaker()

    def get_microphone(self, id, include_loopback):
        self.mic_args = (id, include_loopback)
        sc = self

        class Mic:
            def recorder(self, samplerate, channels):
                sc.rec_args = (samplerate, channels)
                return sc.recorder_obj
        return Mic()


def test_open_loopback_reader_uses_the_default_speakers_loopback_not_the_microphone():
    sc = FakeSC()
    read_block = sl.open_loopback_reader(sc)
    assert sc.mic_args == ("교실 스피커", True)               # include_loopback=True: 마이크가 아니라 스피커로 나가는 소리
    assert sc.rec_args == (sl.SAMPLE_RATE, 1) and sc.recorder_obj.entered
    block = read_block()
    assert len(block) == int(sl.SAMPLE_RATE * sl.SAMPLE_SECONDS) and sl.rms_db(block) == pytest.approx(-12.0, abs=0.1)


# ── 켜기·끄기·상태 ──

def test_start_spawns_once_and_writes_the_pid_file(tmp_path):
    spawned = []
    message = sl.start(tmp_path, spawn=lambda: spawned.append(1) or 777, alive=lambda pid: False, have_package=True)
    assert spawned == [1] and "777" in message and (tmp_path / sl.PID_FILE).read_text(encoding="utf-8") == "777"


def test_start_twice_does_not_spawn_a_second_recorder(tmp_path):
    (tmp_path / sl.PID_FILE).write_text("777", encoding="utf-8")
    spawned = []
    assert sl.start(tmp_path, spawn=lambda: spawned.append(1) or 888, alive=lambda pid: pid == 777, have_package=True) == "이미 켜져 있어요."
    assert spawned == [] and (tmp_path / sl.PID_FILE).read_text(encoding="utf-8") == "777"


def test_start_with_a_stale_pid_file_starts_again(tmp_path):
    (tmp_path / sl.PID_FILE).write_text("777", encoding="utf-8")
    assert "888" in sl.start(tmp_path, spawn=lambda: 888, alive=lambda pid: False, have_package=True)
    assert (tmp_path / sl.PID_FILE).read_text(encoding="utf-8") == "888"


def test_start_without_the_package_only_explains_and_starts_nothing(tmp_path):
    spawned = []
    message = sl.start(tmp_path, spawn=lambda: spawned.append(1) or 1, alive=lambda pid: False, have_package=False)
    assert message == sl.INSTALL_HELP and "pip install soundcard" in message
    assert spawned == [] and not (tmp_path / sl.PID_FILE).exists()


def test_stop_kills_the_running_recorder_and_removes_the_pid_file(tmp_path):
    (tmp_path / sl.PID_FILE).write_text("777", encoding="utf-8")
    killed = []
    assert sl.stop(tmp_path, alive=lambda pid: True, kill=killed.append) == "껐어요."
    assert killed == [777] and not (tmp_path / sl.PID_FILE).exists()


def test_stop_when_nothing_runs_kills_nothing_and_cleans_a_stale_file(tmp_path):
    killed = []
    assert sl.stop(tmp_path, alive=lambda pid: False, kill=killed.append) == "켜져 있지 않아요."
    (tmp_path / sl.PID_FILE).write_text("777", encoding="utf-8")
    assert sl.stop(tmp_path, alive=lambda pid: False, kill=killed.append) == "켜져 있지 않아요."
    assert killed == [] and not (tmp_path / sl.PID_FILE).exists()


def test_status_reports_running_pid_and_last_row(tmp_path):
    (tmp_path / sl.PID_FILE).write_text("777", encoding="utf-8")
    path = sl.level_path(tmp_path, date(2026, 11, 28))
    path.parent.mkdir(parents=True)
    path.write_text("2026-11-28T10:00:00,-30.0\n2026-11-28T10:00:07,-31.0\n", encoding="utf-8")
    info = sl.status(tmp_path, alive=lambda pid: True, today=date(2026, 11, 28))
    assert info == {"running": True, "pid": 777, "last_row": datetime(2026, 11, 28, 10, 0, 7)}
    assert sl.status_text(info) == "켜져 있어요(pid 777), 마지막 기록 10:00:07"


def test_status_not_running_ignores_a_dead_pid(tmp_path):
    (tmp_path / sl.PID_FILE).write_text("777", encoding="utf-8")
    info = sl.status(tmp_path, alive=lambda pid: False, today=date(2026, 11, 28))
    assert info == {"running": False, "pid": None, "last_row": None}
    assert sl.status_text(info) == "꺼져 있어요"


@pytest.mark.parametrize("content", ["", "abc", "-5"])
def test_status_with_a_broken_pid_file_is_not_running(tmp_path, content):
    (tmp_path / sl.PID_FILE).write_text(content, encoding="utf-8")
    assert sl.status(tmp_path, today=date(2026, 11, 28))["running"] is False


@pytest.mark.parametrize("pid", [None, "x", 0, -3])
def test_pid_alive_rejects_nonsense(pid):
    assert sl.pid_alive(pid) is False
