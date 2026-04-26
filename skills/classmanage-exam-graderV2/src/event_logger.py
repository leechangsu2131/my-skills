"""
JSONL 이벤트 로거 — data/logs/YYYY-MM-DD.jsonl 에 append
"""
import json
import logging
from datetime import datetime
from pathlib import Path

_LOG_DIR: Path | None = None


def init(log_dir: Path):
    global _LOG_DIR
    _LOG_DIR = log_dir
    _LOG_DIR.mkdir(parents=True, exist_ok=True)


def log_event(event: str, detail: dict = None):
    if _LOG_DIR is None:
        return
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "event": event,
        "detail": detail or {}
    }
    day_file = _LOG_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.jsonl"
    with open(day_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    logging.info(f"[{event}] {json.dumps(detail or {}, ensure_ascii=False)}")
