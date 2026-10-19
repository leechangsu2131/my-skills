from __future__ import annotations

from pathlib import Path

from .models import TranscriptSegment


def _srt_timestamp(seconds: float) -> str:
    """Format a non-negative timestamp as HH:MM:SS,mmm."""
    total_ms = max(0, int(round(float(seconds) * 1000)))
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d},{milliseconds:03d}"


def export_transcript(segments: list[TranscriptSegment], output_dir: Path) -> tuple[Path, Path]:
    """Write a readable, timestamped TXT and standard SRT transcript."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    txt_path = output_dir / "transcript.txt"
    srt_path = output_dir / "transcript.srt"

    txt_lines: list[str] = []
    srt_blocks: list[str] = []
    for segment in segments:
        text = " ".join((segment.text or "").replace("\r", " ").replace("\n", " ").split())
        if not text:
            continue
        txt_lines.append(f"[{_srt_timestamp(segment.start)}] {text}")
        # Number by emitted blocks so skipped (empty) segments never leave gaps.
        srt_blocks.append(
            f"{len(srt_blocks) + 1}\n{_srt_timestamp(segment.start)} --> {_srt_timestamp(segment.end)}\n{text}"
        )

    txt_path.write_text("\n".join(txt_lines) + ("\n" if txt_lines else ""), encoding="utf-8-sig")
    srt_path.write_text("\n\n".join(srt_blocks) + ("\n" if srt_blocks else ""), encoding="utf-8-sig")
    return txt_path, srt_path
