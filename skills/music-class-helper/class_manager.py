import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


DATA_FILE = Path(__file__).with_name("lesson_manager_data.json")
DEFAULT_DATA = {"saved_classes": [], "recent_runs": []}


def _storage_path(storage_path: Optional[Path] = None) -> Path:
    return Path(storage_path) if storage_path else DATA_FILE


def load_data(storage_path: Optional[Path] = None) -> Dict[str, List[Dict[str, Any]]]:
    path = _storage_path(storage_path)
    if not path.exists():
        return {"saved_classes": [], "recent_runs": []}

    try:
        with path.open("r", encoding="utf-8") as handle:
            loaded = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {"saved_classes": [], "recent_runs": []}

    data = DEFAULT_DATA.copy()
    data.update(loaded if isinstance(loaded, dict) else {})
    data["saved_classes"] = data.get("saved_classes") or []
    data["recent_runs"] = data.get("recent_runs") or []
    return data


def save_data(data: Dict[str, List[Dict[str, Any]]], storage_path: Optional[Path] = None) -> None:
    path = _storage_path(storage_path)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def list_saved_classes(storage_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    data = load_data(storage_path)
    return sorted(data["saved_classes"], key=lambda item: item["name"].lower())


def get_saved_class(name: str, storage_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    lowered = name.lower()
    for item in load_data(storage_path)["saved_classes"]:
        if item.get("name", "").lower() == lowered:
            return item
    return None


def add_saved_class(
    name: str,
    unit: str,
    lesson: str,
    pdf_path: Optional[str] = None,
    exact_title: Optional[str] = None,
    storage_path: Optional[Path] = None,
) -> Dict[str, Any]:
    data = load_data(storage_path)
    entry = {
        "name": name.strip(),
        "unit": unit.strip(),
        "lesson": lesson.strip(),
        "pdf_path": (pdf_path or "").strip(),
        "exact_title": (exact_title or "").strip(),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }

    saved_classes = data["saved_classes"]
    for index, saved in enumerate(saved_classes):
        if saved.get("name", "").lower() == entry["name"].lower():
            saved_classes[index] = entry
            save_data(data, storage_path)
            return entry

    saved_classes.append(entry)
    save_data(data, storage_path)
    return entry


def delete_saved_class(name: str, storage_path: Optional[Path] = None) -> bool:
    data = load_data(storage_path)
    before_count = len(data["saved_classes"])
    lowered = name.lower()
    data["saved_classes"] = [
        item for item in data["saved_classes"] if item.get("name", "").lower() != lowered
    ]
    changed = len(data["saved_classes"]) != before_count
    if changed:
        save_data(data, storage_path)
    return changed


def update_saved_class(
    name: str,
    *,
    unit: Optional[str] = None,
    lesson: Optional[str] = None,
    pdf_path: Optional[str] = None,
    exact_title: Optional[str] = None,
    storage_path: Optional[Path] = None,
) -> Optional[Dict[str, Any]]:
    data = load_data(storage_path)
    lowered = name.lower()
    for index, item in enumerate(data["saved_classes"]):
        if item.get("name", "").lower() != lowered:
            continue

        if unit is not None:
            item["unit"] = unit.strip()
        if lesson is not None:
            item["lesson"] = lesson.strip()
        if pdf_path is not None:
            item["pdf_path"] = pdf_path.strip()
        if exact_title is not None:
            item["exact_title"] = exact_title.strip()
        item["updated_at"] = datetime.now().isoformat(timespec="seconds")
        data["saved_classes"][index] = item
        save_data(data, storage_path)
        return item
    return None


def record_recent_run(
    unit: str,
    lesson: str,
    pdf_path: Optional[str] = None,
    exact_title: Optional[str] = None,
    saved_name: Optional[str] = None,
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
            "pdf_path": (pdf_path or "").strip(),
            "exact_title": (exact_title or "").strip(),
            "saved_name": (saved_name or "").strip(),
            "ran_at": datetime.now().isoformat(timespec="seconds"),
        },
    )
    data["recent_runs"] = recent_runs[:limit]
    save_data(data, storage_path)
    return data["recent_runs"][0]


def list_recent_runs(limit: int = 10, storage_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    data = load_data(storage_path)
    return data["recent_runs"][:limit]
