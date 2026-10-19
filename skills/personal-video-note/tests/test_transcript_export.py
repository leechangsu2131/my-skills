from pathlib import Path

from lecturecapture.models import TranscriptSegment
from lecturecapture.transcript_export import export_transcript


def test_exports_timestamped_txt_and_valid_srt(tmp_path: Path):
    segments = [
        TranscriptSegment(1.2, 2.5, "안녕하세요.\n반갑습니다.", source="faster-whisper-cuda"),
        TranscriptSegment(3661.04, 3662.0, "두 번째 문장", source="subtitle"),
    ]
    txt_path, srt_path = export_transcript(segments, tmp_path)

    txt = txt_path.read_text(encoding="utf-8-sig")
    srt = srt_path.read_text(encoding="utf-8-sig")
    assert txt_path.name == "transcript.txt"
    assert srt_path.name == "transcript.srt"
    assert "[00:00:01,200] 안녕하세요. 반갑습니다." in txt
    assert "[01:01:01,040] 두 번째 문장" in txt
    assert "1\n00:00:01,200 --> 00:00:02,500\n안녕하세요. 반갑습니다." in srt
    assert "2\n01:01:01,040 --> 01:01:02,000\n두 번째 문장" in srt


def test_empty_transcript_exports_empty_files(tmp_path: Path):
    txt_path, srt_path = export_transcript([], tmp_path)
    assert txt_path.read_text(encoding="utf-8-sig") == ""
    assert srt_path.read_text(encoding="utf-8-sig") == ""


def test_srt_numbers_stay_sequential_when_empty_segments_are_skipped(tmp_path: Path):
    segments = [
        TranscriptSegment(1.0, 2.0, "첫 문장"),
        TranscriptSegment(2.0, 3.0, "   "),
        TranscriptSegment(3.0, 4.0, "셋째 문장"),
    ]
    _, srt_path = export_transcript(segments, tmp_path)
    blocks = srt_path.read_text(encoding="utf-8-sig").strip().split("\n\n")
    assert [b.splitlines()[0] for b in blocks] == ["1", "2"]
    assert blocks[1].splitlines()[2] == "셋째 문장"
