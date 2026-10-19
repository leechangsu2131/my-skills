from pathlib import Path

from lecturecapture.subtitles import parse_subtitles


def test_parse_srt(tmp_path: Path):
    subtitle = tmp_path / "sample.srt"
    subtitle.write_text(
        "1\n00:00:01,200 --> 00:00:02,500\n안녕하세요.\n\n"
        "2\n00:00:03,000 --> 00:00:04,100\n<b>두 번째 줄</b>\n",
        encoding="utf-8",
    )
    segments = parse_subtitles(subtitle)
    assert len(segments) == 2
    assert segments[0].start == 1.2
    assert segments[0].end == 2.5
    assert segments[1].text == "두 번째 줄"


def test_parse_vtt(tmp_path: Path):
    subtitle = tmp_path / "sample.vtt"
    subtitle.write_text("WEBVTT\n\n00:00:05.000 --> 00:00:06.250\n자막\n", encoding="utf-8")
    segments = parse_subtitles(subtitle)
    assert len(segments) == 1
    assert segments[0].start == 5.0
    assert segments[0].end == 6.25
