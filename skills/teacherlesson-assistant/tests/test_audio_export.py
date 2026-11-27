"""audio_export.py(녹음 → 클로바노트용 MP3) 시험 (T99).

    python -m pytest tests -v      (teacherlesson-assistant 폴더에서)

대부분 가짜 변환기(runner)로 돈다. 진짜 ffmpeg 가 PATH 에 있을 때만 도는 시험이 하나 있다(없으면 건너뜀).
임시 폴더만 쓰고 실제 녹음·내 문서는 건드리지 않는다.
"""
import os
import pathlib
import re
import shutil
import subprocess
import sys
import threading
import time

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import audio_export as ae  # noqa: E402


# ── 도우미 ──

def make_src(tmp_path, name="3교시_국어_101500.webm", data=b"WEBM-DATA", age=3600):
    src = tmp_path / "2026-11-27" / name
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_bytes(data)
    old = time.time() - age
    os.utime(src, (old, old))
    return src


class FakeRunner:
    """ffmpeg 흉내: 마지막 인자(출력 경로)에 파일을 쓰고, 부른 기록을 남긴다."""

    def __init__(self, returncode=0, stderr=b"", output=b"MP3-DATA", raises=None, delay=0.0):
        self.calls, self.returncode, self.stderr, self.output, self.raises, self.delay = [], returncode, stderr, output, raises, delay
        self.stdin_data = []

    def __call__(self, cmd, **kw):
        self.calls.append((cmd, kw))
        self.stdin_data.append(kw["stdin"].read())
        if self.delay:
            time.sleep(self.delay)
        if self.raises:
            raise self.raises
        if self.returncode == 0 and self.output is not None:
            pathlib.Path(cmd[-1]).write_bytes(self.output)
        return subprocess.CompletedProcess(cmd, self.returncode, stdout=b"", stderr=self.stderr)


# ── find_ffmpeg ──

def test_find_ffmpeg_prefers_existing_configured_path():
    assert ae.find_ffmpeg({"ffmpeg_path": "D:/ff/ffmpeg.exe"}, which=lambda n: "/usr/bin/ffmpeg", is_file=lambda p: True) == "D:/ff/ffmpeg.exe"


def test_find_ffmpeg_ignores_configured_path_that_is_not_a_file():
    assert ae.find_ffmpeg({"ffmpeg_path": "D:/없음/ffmpeg.exe"}, which=lambda n: "/usr/bin/ffmpeg", is_file=lambda p: False) == "/usr/bin/ffmpeg"


@pytest.mark.parametrize("cfg", [None, {}, {"ffmpeg_path": ""}, {"ffmpeg_path": "   "}, {"ffmpeg_path": None}])
def test_find_ffmpeg_without_setting_uses_path_search(cfg):
    asked = []
    assert ae.find_ffmpeg(cfg, which=lambda n: asked.append(n) or "/bin/ffmpeg") == "/bin/ffmpeg" and asked == ["ffmpeg"]


def test_find_ffmpeg_nothing_found_is_none():
    assert ae.find_ffmpeg({}, which=lambda n: None) is None


# ── export_path · is_still_recording · build_command ──

def test_export_path_goes_next_to_the_original_in_export_folder(tmp_path):
    src = tmp_path / "2026-11-27" / "3교시_국어.webm"
    assert ae.export_path(src, "mp3") == tmp_path / "2026-11-27" / "export" / "3교시_국어.mp3"
    assert ae.export_path(src, "m4a").name == "3교시_국어.m4a"


def test_export_path_rejects_unknown_format(tmp_path):
    with pytest.raises(ValueError):
        ae.export_path(tmp_path / "a.webm", "wav")


def test_is_still_recording_uses_the_last_change_time(tmp_path):
    src = make_src(tmp_path, age=0)
    now = src.stat().st_mtime
    assert ae.is_still_recording(src, now=now + 5) is True
    assert ae.is_still_recording(src, now=now + 29) is True
    assert ae.is_still_recording(src, now=now + 30) is False
    assert ae.is_still_recording(src, now=now + 3600) is False
    assert ae.is_still_recording(src, now=now + 10, quiet_seconds=5) is False


def test_build_command_mono_24k_64k_from_stdin(tmp_path):
    cmd = ae.build_command("ffmpeg", tmp_path / "o.mp3", "mp3")
    assert cmd[0] == "ffmpeg" and cmd[-1] == str(tmp_path / "o.mp3")
    assert cmd[cmd.index("-i") + 1] == "pipe:0"
    assert cmd[cmd.index("-ac") + 1] == "1" and cmd[cmd.index("-ar") + 1] == "24000"
    assert cmd[cmd.index("-c:a") + 1] == "libmp3lame" and cmd[cmd.index("-b:a") + 1] == "64k"
    assert "-vn" in cmd and "-y" in cmd


def test_build_command_m4a_uses_aac(tmp_path):
    cmd = ae.build_command("ffmpeg", tmp_path / "o.m4a", "m4a")
    assert cmd[cmd.index("-c:a") + 1] == "aac"


# ── convert ──

def test_convert_streams_original_through_stdin_and_names_result_in_korean(tmp_path):
    src = make_src(tmp_path)
    runner = FakeRunner()
    out = ae.convert(src, "mp3", "ffmpeg", runner=runner)
    assert out == src.parent / "export" / "3교시_국어_101500.mp3"
    assert out.read_bytes() == b"MP3-DATA"
    assert runner.stdin_data == [b"WEBM-DATA"]                     # 원본이 표준입력으로 들어감
    cmd, kw = runner.calls[0]
    assert re.fullmatch(r"tmp_[0-9a-f]{8}\.mp3", pathlib.Path(cmd[-1]).name)     # 출력은 영문 임시 이름
    assert str(src) not in cmd                                      # 한글 원본 경로를 명령에 안 넣음
    assert kw["timeout"] == ae.TIMEOUT_SECONDS
    assert [p.name for p in out.parent.iterdir()] == [out.name]     # 임시 파일이 남지 않음


def test_convert_never_touches_the_original(tmp_path):
    src = make_src(tmp_path)
    before = (src.read_bytes(), src.stat().st_mtime)
    ae.convert(src, "mp3", "ffmpeg", runner=FakeRunner())
    assert (src.read_bytes(), src.stat().st_mtime) == before


def test_convert_without_ffmpeg_gives_install_help(tmp_path):
    with pytest.raises(ae.FfmpegMissing, match="winget install Gyan.FFmpeg"):
        ae.convert(make_src(tmp_path), "mp3", None, runner=FakeRunner())


def test_convert_failure_reports_last_error_line_and_leaves_nothing(tmp_path):
    src = make_src(tmp_path)
    runner = FakeRunner(returncode=1, stderr="첫 줄\n  \nInvalid data found when processing input\n".encode())
    with pytest.raises(ae.ExportError, match="Invalid data found"):
        ae.convert(src, "mp3", "ffmpeg", runner=runner)
    assert not (src.parent / "export" / "3교시_국어_101500.mp3").exists()
    assert list((src.parent / "export").iterdir()) == []


def test_convert_failure_with_empty_stderr_still_has_a_message(tmp_path):
    with pytest.raises(ae.ExportError, match="알 수 없는 오류"):
        ae.convert(make_src(tmp_path), "mp3", "ffmpeg", runner=FakeRunner(returncode=1))


def test_convert_empty_or_missing_output_is_an_error(tmp_path):
    for output in (b"", None):
        src = make_src(tmp_path)
        with pytest.raises(ae.ExportError, match="비어"):
            ae.convert(src, "mp3", "ffmpeg", runner=FakeRunner(output=output))
        assert list((src.parent / "export").iterdir()) == []


def test_convert_timeout_is_an_error_with_the_seconds(tmp_path):
    runner = FakeRunner(raises=subprocess.TimeoutExpired("ffmpeg", 300))
    with pytest.raises(ae.ExportError, match="300초"):
        ae.convert(make_src(tmp_path), "mp3", "ffmpeg", runner=runner)


def test_convert_cannot_start_ffmpeg_is_an_error(tmp_path):
    with pytest.raises(ae.ExportError, match="실행하지 못했어요"):
        ae.convert(make_src(tmp_path), "mp3", "ffmpeg", runner=FakeRunner(raises=FileNotFoundError("ffmpeg")))


def test_convert_missing_original_and_bad_format(tmp_path):
    with pytest.raises(ae.ExportError, match="찾지 못했어요"):
        ae.convert(tmp_path / "없음.webm", "mp3", "ffmpeg", runner=FakeRunner())
    with pytest.raises(ae.ExportError, match="지원하지 않는"):
        ae.convert(make_src(tmp_path), "wav", "ffmpeg", runner=FakeRunner())


def test_convert_reuses_a_newer_result_and_redoes_it_when_the_original_grows(tmp_path):
    src = make_src(tmp_path)
    runner = FakeRunner()
    first = ae.convert(src, "mp3", "ffmpeg", runner=runner)
    assert len(runner.calls) == 1
    assert ae.convert(src, "mp3", "ffmpeg", runner=runner) == first and len(runner.calls) == 1     # 그대로 재사용
    src.write_bytes(b"WEBM-DATA-MORE")                       # 녹음이 더 붙어 원본이 새것이 됨
    later = time.time() + 5
    os.utime(src, (later, later))
    runner.output = b"MP3-NEW"
    assert ae.convert(src, "mp3", "ffmpeg", runner=runner).read_bytes() == b"MP3-NEW" and len(runner.calls) == 2


def test_two_formats_are_cached_separately(tmp_path):
    src = make_src(tmp_path)
    runner = FakeRunner()
    mp3, m4a = ae.convert(src, "mp3", "ffmpeg", runner=runner), ae.convert(src, "m4a", "ffmpeg", runner=runner)
    assert mp3.name.endswith(".mp3") and m4a.name.endswith(".m4a") and len(runner.calls) == 2


def test_same_file_requested_twice_at_once_is_converted_once(tmp_path):
    src = make_src(tmp_path)
    runner = FakeRunner(delay=0.3)
    results = []
    threads = [threading.Thread(target=lambda: results.append(ae.convert(src, "mp3", "ffmpeg", runner=runner))) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(10)
    assert len(results) == 3 and len(set(results)) == 1
    assert len(runner.calls) == 1


# ── 진짜 ffmpeg (있을 때만) ──

@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg 가 PATH 에 없음")
def test_real_ffmpeg_turns_a_small_webm_into_an_mp3(tmp_path):
    src = tmp_path / "2026-11-27" / "1교시_수학.webm"
    src.parent.mkdir()
    made = subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
                           "-c:a", "libopus", str(src)], capture_output=True)
    assert made.returncode == 0, made.stderr
    old = time.time() - 3600
    os.utime(src, (old, old))
    out = ae.convert(src, "mp3", shutil.which("ffmpeg"))
    data = out.read_bytes()
    assert out.name == "1교시_수학.mp3" and len(data) > 1000
    assert data[:3] == b"ID3" or data[0] == 0xFF                      # ID3 머리 또는 MP3 프레임
