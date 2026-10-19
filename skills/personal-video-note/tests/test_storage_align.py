from pathlib import Path

from lecturecapture.align import align_transcript_to_slides
from lecturecapture.models import SlideEvent, TranscriptSegment
from lecturecapture.storage import atomic_write_json, read_json


def test_atomic_json_roundtrip_and_backup(tmp_path: Path):
    path = tmp_path / "project.json"
    backup = tmp_path / "backups"
    atomic_write_json(path, {"version": 1}, backup)
    atomic_write_json(path, {"version": 2}, backup)
    assert read_json(path)["version"] == 2
    assert len(list(backup.glob("*.json"))) == 1


def test_transcript_alignment_by_overlap():
    slide = SlideEvent("s1", "slides/s1.jpg", 1, 2.5, 2, 1, 5, 4, 4, "aabb")
    transcript = [
        TranscriptSegment(0, 1, "before"),
        TranscriptSegment(2, 3, "inside"),
        TranscriptSegment(5, 6, "after"),
    ]
    align_transcript_to_slides([slide], transcript)
    assert [seg.text for seg in slide.transcript] == ["inside"]
