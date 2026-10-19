from __future__ import annotations

from .models import SlideEvent, TranscriptSegment


def align_transcript_to_slides(slides: list[SlideEvent], transcript: list[TranscriptSegment]) -> list[SlideEvent]:
    """Attach transcript segments by interval overlap; retain source transcript separately too."""
    for slide in slides:
        slide.transcript = [
            segment for segment in transcript
            if segment.end > slide.start_time and segment.start < slide.end_time
        ]
    return slides
