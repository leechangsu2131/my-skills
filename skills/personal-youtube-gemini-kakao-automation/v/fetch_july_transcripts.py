import json
import os
import subprocess
import sys

from main import _vtt_to_text, get_transcript_via_ytdlp, load_settings

TARGETS = [
    ("2026-07-02", "LyEVQyARiIQ"),
    ("2026-07-03", "nH6kcxUlP9Q"),
    ("2026-07-06", "VekT-WWwZUA"),
    ("2026-07-07", "S9-LxKtwveg"),
    ("2026-07-08", "phpzOVwWIOQ"),
    ("2026-07-09", "xmPUTJuLvQo"),
]


def main() -> None:
    settings = load_settings()
    out_dir = os.path.join(os.path.dirname(__file__), "backlog_transcripts")
    os.makedirs(out_dir, exist_ok=True)
    for day, vid in TARGETS:
        path = os.path.join(out_dir, f"{day}_{vid}.txt")
        if os.path.exists(path) and os.path.getsize(path) > 1000:
            print("skip", day, vid)
            continue
        text = get_transcript_via_ytdlp(settings, vid)
        if not text:
            print("fail", day, vid)
            continue
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        print("ok", day, vid, len(text))


if __name__ == "__main__":
    main()
