from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


DATA_FILE = Path(__file__).with_name("social_class_data.json")
DEFAULT_DATA = {"saved_lessons": [], "recent_runs": []}


def _storage_path(storage_path: Optional[Path] = None) -> Path:
    return Path(storage_path) if storage_path else DATA_FILE


def load_data(storage_path: Optional[Path] = None) -> Dict[str, List[Dict[str, Any]]]:
    path = _storage_path(storage_path)
    if not path.exists():
        return {"saved_lessons": [], "recent_runs": []}

    try:
        with path.open("r", encoding="utf-8") as handle:
            loaded = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {"saved_lessons": [], "recent_runs": []}

    data = DEFAULT_DATA.copy()
    data.update(loaded if isinstance(loaded, dict) else {})
    data["saved_lessons"] = data.get("saved_lessons") or []
    data["recent_runs"] = data.get("recent_runs") or []
    return data


def save_data(data: Dict[str, List[Dict[str, Any]]], storage_path: Optional[Path] = None) -> None:
    path = _storage_path(storage_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def list_saved_lessons(storage_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    data = load_data(storage_path)
    return sorted(data["saved_lessons"], key=lambda item: item["name"].lower())


def get_saved_lesson(name: str, storage_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    lowered = name.lower()
    for item in load_data(storage_path)["saved_lessons"]:
        if item.get("name", "").lower() == lowered:
            return item
    return None


def upsert_saved_lesson(
    name: str,
    unit: str,
    lesson: str,
    exact_title: Optional[str] = None,
    guide_pdf_path: Optional[str] = None,
    storage_path: Optional[Path] = None,
) -> Dict[str, Any]:
    data = load_data(storage_path)
    entry = {
        "name": name.strip(),
        "unit": unit.strip(),
        "lesson": lesson.strip(),
        "exact_title": (exact_title or "").strip(),
        "guide_pdf_path": (guide_pdf_path or "").strip(),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }

    saved_lessons = data["saved_lessons"]
    for index, saved in enumerate(saved_lessons):
        if saved.get("name", "").lower() == entry["name"].lower():
            if not entry["guide_pdf_path"] and saved.get("guide_pdf_path"):
                entry["guide_pdf_path"] = saved.get("guide_pdf_path", "")
            saved_lessons[index] = entry
            save_data(data, storage_path)
            return entry

    saved_lessons.append(entry)
    save_data(data, storage_path)
    return entry


def delete_saved_lesson(name: str, storage_path: Optional[Path] = None) -> bool:
    data = load_data(storage_path)
    lowered = name.lower()
    before_count = len(data["saved_lessons"])
    data["saved_lessons"] = [
        item for item in data["saved_lessons"] if item.get("name", "").lower() != lowered
    ]
    changed = len(data["saved_lessons"]) != before_count
    if changed:
        save_data(data, storage_path)
    return changed


def record_recent_run(
    unit: str,
    lesson: str,
    exact_title: Optional[str] = None,
    saved_name: Optional[str] = None,
    guide_pdf_path: Optional[str] = None,
    storage_path: Optional[Path] = None,
    limit: int = 10,
) -> Dict[str, Any]:
    data = load_data(storage_path)
    recent_runs = data["recent_runs"]
    recent_runs.insert(
        0,
        {
            "unit": unit.strip(),
            "lesson": lesson.strip(),
            "exact_title": (exact_title or "").strip(),
            "saved_name": (saved_name or "").strip(),
            "guide_pdf_path": (guide_pdf_path or "").strip(),
            "ran_at": datetime.now().isoformat(timespec="seconds"),
        },
    )
    data["recent_runs"] = recent_runs[:limit]
    save_data(data, storage_path)
    return data["recent_runs"][0]


def list_recent_runs(limit: int = 10, storage_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    data = load_data(storage_path)
    return data["recent_runs"][:limit]
