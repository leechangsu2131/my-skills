import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


APP_VERSION = "2.0"
PROJECT_FILENAME = "project.json"


@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    project_json: Path
    template_dir: Path
    answers_dir: Path
    student_pdf_dir: Path
    student_page_dir: Path
    aligned_dir: Path
    json_dir: Path
    yolo_dir: Path
    logs_dir: Path
    artifacts_dir: Path
    submissions_dir: Path
    crops_dir: Path
    exports_dir: Path


def _now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def _default_root_dir() -> Path:
    return Path.home() / "Documents" / "ClassExamGrade"


def slugify_project_name(name: str) -> str:
    slug = re.sub(r'[<>:"/\\|?*]+', "_", (name or "").strip())
    slug = re.sub(r"\s+", "_", slug)
    slug = re.sub(r"_+", "_", slug)
    slug = slug.strip("._ ")
    return slug or "project"


def _normalize_root_dir(value: str | None) -> Path:
    raw = value.strip() if isinstance(value, str) else ""
    root_dir = Path(raw).expanduser() if raw else _default_root_dir()
    return root_dir.resolve()


def _normalize_settings(data: dict | None) -> dict:
    data = data or {}
    root_dir = _normalize_root_dir(data.get("root_dir"))
    
    home_str = str(Path.home())
    root_str = str(root_dir)
    if root_str.startswith(home_str):
        root_str = "~" + root_str[len(home_str):]
        root_str = root_str.replace("\\", "/")
        
    last_project = data.get("last_project") or None
    return {
        "root_dir": root_str,
        "last_project": last_project,
        "app_version": APP_VERSION,
    }


def load_settings(settings_path: Path) -> dict:
    if settings_path.exists():
        try:
            data = json.loads(settings_path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    else:
        data = {}
    return save_settings(settings_path, data)


def save_settings(settings_path: Path, data: dict | None) -> dict:
    settings = _normalize_settings(data)
    root_dir = Path(settings["root_dir"]).expanduser().resolve()
    root_dir.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return settings


def project_paths(project_dir: Path) -> ProjectPaths:
    return ProjectPaths(
        root=project_dir,
        project_json=project_dir / PROJECT_FILENAME,
        template_dir=project_dir / "template",
        answers_dir=project_dir / "answers",
        student_pdf_dir=project_dir / "students" / "raw",
        student_page_dir=project_dir / "students" / "raw_pages",
        aligned_dir=project_dir / "students" / "aligned",
        json_dir=project_dir / "json",
        yolo_dir=project_dir / "yolo_labels",
        logs_dir=project_dir / "logs",
        artifacts_dir=project_dir / "artifacts",
        submissions_dir=project_dir / "artifacts" / "submissions",
        crops_dir=project_dir / "artifacts" / "crops",
        exports_dir=project_dir / "artifacts" / "exports",
    )


def _ensure_project_dirs(paths: ProjectPaths) -> None:
    for directory in (
        paths.root,
        paths.template_dir,
        paths.answers_dir,
        paths.student_pdf_dir,
        paths.student_page_dir,
        paths.aligned_dir,
        paths.json_dir,
        paths.yolo_dir,
        paths.logs_dir,
        paths.artifacts_dir,
        paths.submissions_dir,
        paths.crops_dir,
        paths.exports_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)


def _default_project_data(payload: dict, slug: str) -> dict:
    now = _now_iso()
    return {
        "name": payload.get("name") or slug,
        "slug": slug,
        "created_at": now,
        "updated_at": now,
        "subject": payload.get("subject", ""),
        "grade": payload.get("grade", ""),
        "class": payload.get("class", ""),
        "exam_name": payload.get("exam_name", ""),
        "template_pages": 0,
        "total_questions": 0,
        "student_count": 0,
        "status": {
            "template_ready": False,
            "regions_ready": False,
            "alignment_done": False,
            "review_done": False,
        },
    }


def create_project(root_dir: Path, payload: dict) -> dict:
    name = (payload.get("name") or "").strip()
    if not name:
        raise ValueError("Project name is required")

    root_dir.mkdir(parents=True, exist_ok=True)
    slug = slugify_project_name(name)
    project_dir = root_dir / slug
    if project_dir.exists():
        raise FileExistsError(f"Project already exists: {slug}")

    paths = project_paths(project_dir)
    _ensure_project_dirs(paths)
    data = _default_project_data(payload, slug)
    paths.project_json.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return data


def resolve_project_dir(root_dir: Path, slug: str) -> Path:
    return root_dir / slug


def _load_project_json(project_dir: Path) -> dict:
    data = json.loads((project_dir / PROJECT_FILENAME).read_text(encoding="utf-8"))
    if "status" not in data or not isinstance(data["status"], dict):
        data["status"] = {}
    data.setdefault("slug", project_dir.name)
    return data


def _extract_page_numbers(questions: list[dict]) -> list[int]:
    pages = sorted(
        {
            int(q.get("page", 1))
            for q in questions
            if isinstance(q, dict)
        }
    )
    return pages


def _count_students(paths: ProjectPaths) -> int:
    ids = set()
    for pattern_dir in (paths.student_page_dir, paths.aligned_dir):
        for path in pattern_dir.glob("*"):
            if not path.is_file():
                continue
            match = re.search(r"_stu(\d+)_", path.name, re.IGNORECASE)
            if match:
                ids.add(match.group(1))
    if ids:
        return len(ids)
    return sum(1 for path in paths.student_pdf_dir.glob("*.pdf") if path.is_file())


def refresh_project_metadata(project_dir: Path, touch: bool = False) -> dict:
    paths = project_paths(project_dir)
    _ensure_project_dirs(paths)
    data = _load_project_json(project_dir)

    template_files = sorted(
        p.name for p in paths.template_dir.glob("blank_*.png") if p.is_file()
    )
    regions_path = paths.json_dir / "regions.json"
    questions: list[dict] = []
    if regions_path.exists():
        try:
            regions_data = json.loads(regions_path.read_text(encoding="utf-8"))
            questions = regions_data.get("questions", [])
            if not isinstance(questions, list):
                questions = []
        except Exception:
            questions = []

    raw_page_count = sum(
        1
        for p in paths.student_page_dir.glob("*")
        if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png"}
    )
    aligned_count = sum(
        1
        for p in paths.aligned_dir.glob("*")
        if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png"}
    )
    yolo_count = sum(1 for p in paths.yolo_dir.glob("*.txt") if p.is_file())

    data["template_pages"] = len(template_files)
    data["total_questions"] = len(questions)
    data["student_count"] = _count_students(paths)
    if touch:
        data["updated_at"] = _now_iso()
    else:
        data.setdefault("updated_at", data.get("created_at", _now_iso()))
    data["status"] = {
        "template_ready": len(template_files) > 0,
        "regions_ready": len(questions) > 0,
        "alignment_done": raw_page_count > 0 and aligned_count >= raw_page_count,
        "review_done": yolo_count > 0,
    }

    paths.project_json.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return data


def scan_projects(root_dir: Path) -> list[dict]:
    root_dir.mkdir(parents=True, exist_ok=True)
    projects = []
    for path in root_dir.iterdir():
        if not path.is_dir():
            continue
        if not (path / PROJECT_FILENAME).exists():
            continue
        try:
            projects.append(refresh_project_metadata(path, touch=False))
        except Exception:
            continue
    projects.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
    return projects


def get_project_status(project_dir: Path) -> dict:
    paths = project_paths(project_dir)
    project = refresh_project_metadata(project_dir, touch=False)

    templates = sorted(
        p.name
        for p in paths.template_dir.iterdir()
        if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png"} and p.name.startswith("blank_")
    )
    answers = sorted(
        p.name for p in paths.answers_dir.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"
    )
    students = sorted(
        p.name for p in paths.student_pdf_dir.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"
    )

    regions_path = paths.json_dir / "regions.json"
    regions_info = {"exists": False}
    if regions_path.exists():
        try:
            data = json.loads(regions_path.read_text(encoding="utf-8"))
            qs = data.get("questions", [])
            if not isinstance(qs, list):
                qs = []
            regions_info = {
                "exists": True,
                "question_count": len(qs),
                "pages": _extract_page_numbers(qs),
                "created_at": datetime.fromtimestamp(regions_path.stat().st_mtime).isoformat(),
            }
        except Exception:
            regions_info = {"exists": False}

    return {
        "project": project,
        "template": {"files": templates, "count": len(templates)},
        "answers": {"files": answers, "count": len(answers)},
        "regions": regions_info,
        "students": {"files": students, "count": len(students)},
    }
