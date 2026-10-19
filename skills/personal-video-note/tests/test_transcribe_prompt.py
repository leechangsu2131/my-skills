from pathlib import Path
import sys
import types

from lecturecapture.transcribe import transcribe_video


def test_initial_prompt_is_forwarded_to_faster_whisper(monkeypatch, tmp_path: Path):
    received = {}

    class FakeSegment:
        start = 0.25
        end = 1.5
        text = " 학생 평가와 기초학력 "

    class FakeModel:
        def __init__(self, model_size, device, compute_type):
            received["init"] = (model_size, device, compute_type)

        def transcribe(self, video, **kwargs):
            received["transcribe"] = kwargs
            return iter([FakeSegment()]), object()

    monkeypatch.setitem(sys.modules, "faster_whisper", types.SimpleNamespace(WhisperModel=FakeModel))
    video = tmp_path / "lecture.mp4"
    video.write_bytes(b"dummy")

    result = transcribe_video(video, initial_prompt="기초학력, 형성평가")

    assert received["init"] == ("large-v3", "cuda", "int8_float16")
    assert received["transcribe"]["initial_prompt"] == "기초학력, 형성평가"
    assert received["transcribe"]["vad_filter"] is True
    assert result[0].text == "학생 평가와 기초학력"
    assert result[0].source == "faster-whisper-cuda"


def test_hotwords_are_forwarded_when_supported(monkeypatch, tmp_path: Path):
    received = {}

    class FakeSegment:
        start, end, text = 0.0, 1.0, "교육연극"

    class FakeModel:
        def __init__(self, model_size, device, compute_type):
            pass

        def transcribe(self, video, language=None, vad_filter=False, initial_prompt=None, hotwords=None):
            received.update(initial_prompt=initial_prompt, hotwords=hotwords)
            return iter([FakeSegment()]), object()

    monkeypatch.setitem(sys.modules, "faster_whisper", types.SimpleNamespace(WhisperModel=FakeModel))
    video = tmp_path / "lecture.mp4"
    video.write_bytes(b"dummy")

    transcribe_video(video, initial_prompt="초등 교육", hotwords=" 교육연극, 행복교실 ")

    assert received == {"initial_prompt": "초등 교육", "hotwords": "교육연극, 행복교실"}


def test_hotwords_are_skipped_with_warning_on_old_faster_whisper(monkeypatch, tmp_path: Path):
    import pytest

    class FakeSegment:
        start, end, text = 0.0, 1.0, "안녕하세요"

    class OldModel:
        def __init__(self, model_size, device, compute_type):
            pass

        # Old API: no hotwords parameter and no **kwargs.
        def transcribe(self, video, language=None, vad_filter=False, initial_prompt=None):
            return iter([FakeSegment()]), object()

    monkeypatch.setitem(sys.modules, "faster_whisper", types.SimpleNamespace(WhisperModel=OldModel))
    video = tmp_path / "lecture.mp4"
    video.write_bytes(b"dummy")

    with pytest.warns(RuntimeWarning, match="hotwords"):
        result = transcribe_video(video, hotwords="교육연극")
    assert result[0].text == "안녕하세요"


def test_empty_hotwords_are_not_sent(monkeypatch, tmp_path: Path):
    received = {}

    class FakeSegment:
        start, end, text = 0.0, 1.0, "x"

    class FakeModel:
        def __init__(self, *args, **kwargs):
            pass

        def transcribe(self, video, **kwargs):
            received.update(kwargs)
            return iter([FakeSegment()]), object()

    monkeypatch.setitem(sys.modules, "faster_whisper", types.SimpleNamespace(WhisperModel=FakeModel))
    video = tmp_path / "lecture.mp4"
    video.write_bytes(b"dummy")
    transcribe_video(video, hotwords="   ")
    assert "hotwords" not in received
