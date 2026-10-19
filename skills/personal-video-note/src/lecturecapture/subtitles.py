from __future__ import annotations

import re
from pathlib import Path

from .models import TranscriptSegment

_TIMESTAMP = re.compile(r"(?P<h>\d{1,2}):(?P<m>\d{2}):(?P<s>\d{2})[,.](?P<ms>\d{1,3})")


def _seconds(match: re.Match[str]) -> float:
    milliseconds = int(match.group("ms").ljust(3, "0")[:3])
    return int(match.group("h")) * 3600 + int(match.group("m")) * 60 + int(match.group("s")) + milliseconds / 1000


def parse_subtitles(path: Path) -> list[TranscriptSegment]:
    """Parse common SRT and WebVTT timestamp blocks without requiring a subtitle library."""
    text = Path(path).read_text(encoding="utf-8-sig", errors="replace")
    blocks = re.split(r"\n\s*\n", text.replace("\r\n", "\n").replace("\r", "\n").strip())
    segments: list[TranscriptSegment] = []
    for block in blocks:
        lines = [line.strip("\ufeff ") for line in block.split("\n") if line.strip()]
        timing_index = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if timing_index is None:
            continue
        left, right = (part.strip().split()[0] for part in lines[timing_index].split("-->", 1))
        start_match = _TIMESTAMP.search(left)
        end_match = _TIMESTAMP.search(right)
        if not start_match or not end_match:
            continue
        start, end = _seconds(start_match), _seconds(end_match)
        body = " ".join(lines[timing_index + 1:]).strip()
        body = re.sub(r"<[^>]+>", "", body)
        body = re.sub(r"\{\\[^}]+\}", "", body).strip()
        if not body or end < start:
            continue
        segments.append(TranscriptSegment(start, end, body, source="subtitle"))
    return sorted(segments, key=lambda seg: (seg.start, seg.end))
