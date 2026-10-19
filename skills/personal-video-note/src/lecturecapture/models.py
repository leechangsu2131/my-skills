from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str
    source: str = "subtitle"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SlideEvent:
    slide_id: str
    image_path: str
    first_seen: float
    stable_from: float
    best_frame_time: float
    start_time: float
    end_time: float
    duration: float
    sharpness: float
    frame_hash: str
    duplicate_of: str | None = None
    occurrences: list[float] = field(default_factory=list)
    transcript: list[TranscriptSegment] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["transcript"] = [seg.to_dict() if isinstance(seg, TranscriptSegment) else seg for seg in self.transcript]
        return d


@dataclass
class Project:
    schema_version: int
    project_id: str
    source_video: str
    source_url: str | None
    duration: float
    fps: float
    width: int
    height: int
    crop: dict[str, int]
    parameters: dict[str, Any]
    slides: list[SlideEvent] = field(default_factory=list)
    transcript: list[TranscriptSegment] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["slides"] = [slide.to_dict() for slide in self.slides]
        d["transcript"] = [seg.to_dict() for seg in self.transcript]
        return d
