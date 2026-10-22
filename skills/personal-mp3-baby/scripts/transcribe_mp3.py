#!/usr/bin/env python3
"""Transcribe an audio file to a Korean SRT using faster-whisper."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def srt_timestamp(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{whole_seconds:02},{milliseconds:03}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio", type=Path, help="Input audio file (for example, MP3)")
    parser.add_argument("--model", default="small", help="Whisper model size (default: small)")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing SRT")
    args = parser.parse_args()

    audio = args.audio.expanduser().resolve()
    if not audio.is_file():
        parser.error(f"Audio file not found: {audio}")
    output = audio.with_suffix(".srt")
    if output.exists() and not args.overwrite:
        parser.error(f"Output already exists; pass --overwrite to replace it: {output}")

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("Install the dependency with: python -m pip install faster-whisper", file=sys.stderr)
        return 2

    device = args.device
    compute_type = "int8"
    if device == "auto":
        try:
            import ctranslate2

            device = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
        except Exception:
            device = "cpu"
    if device == "cuda":
        compute_type = "float16"

    model = WhisperModel(args.model, device=device, compute_type=compute_type)
    segments, _info = model.transcribe(
        str(audio), language="ko", task="transcribe", vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
        beam_size=5,
    )

    temporary = output.with_name(output.name + ".tmp")
    count = 0
    try:
        with temporary.open("w", encoding="utf-8-sig", newline="\n") as handle:
            for segment in segments:
                text = " ".join(segment.text.split()).strip()
                if not text:
                    continue
                count += 1
                handle.write(f"{count}\n")
                handle.write(f"{srt_timestamp(segment.start)} --> {srt_timestamp(segment.end)}\n")
                handle.write(f"{text}\n\n")
        if count == 0:
            temporary.unlink(missing_ok=True)
            print("No speech segments were recognized; no SRT was written.", file=sys.stderr)
            return 1
        temporary.replace(output)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    print(f"Wrote {count} subtitle cues: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
