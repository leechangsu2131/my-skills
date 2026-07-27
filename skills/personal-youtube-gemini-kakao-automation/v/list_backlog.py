# -*- coding: utf-8 -*-
"""Dry-run: list backlog targets without calling Gemini."""
from __future__ import annotations

import datetime
import os

from main import collect_backlog_targets, load_processed_ids, load_settings, _parse_yyyymmdd


def main() -> None:
    settings = load_settings()
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    from_date = _parse_yyyymmdd(os.getenv("BACKLOG_FROM", "")) or (today - datetime.timedelta(days=7))
    to_date = _parse_yyyymmdd(os.getenv("BACKLOG_TO", "")) or yesterday
    processed = load_processed_ids(settings.processed_file)
    include_weekends = os.getenv("BACKLOG_INCLUDE_WEEKENDS", "1").strip().lower() in {"1", "true", "yes"}
    targets = collect_backlog_targets(
        settings,
        from_date,
        to_date,
        processed,
        include_weekends=include_weekends,
    )
    print(f"Range: {from_date} .. {to_date} | targets: {len(targets)}")
    for upload_date, video_id, title in targets:
        print(f"{upload_date} {video_id} {title}")


if __name__ == "__main__":
    main()
