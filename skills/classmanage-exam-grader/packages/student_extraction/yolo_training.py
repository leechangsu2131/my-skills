from __future__ import annotations

from pathlib import Path
from typing import Any
from typing import Sequence


DEFAULT_ANSWER_REGION_CLASS_NAMES = (
    "choice_answer_region",
    "short_answer_line",
    "descriptive_answer_area",
)

DEFAULT_DATASET_SUBDIRS = (
    Path("images/train"),
    Path("images/val"),
    Path("labels/train"),
    Path("labels/val"),
)


def initialize_answer_region_dataset(
    dataset_root: str | Path,
    *,
    class_names: Sequence[str] | None = None,
) -> Path:
    root = Path(dataset_root)
    names = _normalize_class_names(class_names)

    for relative_dir in DEFAULT_DATASET_SUBDIRS:
        (root / relative_dir).mkdir(parents=True, exist_ok=True)

    data_yaml_path = root / "data.yaml"
    data_yaml_path.write_text(_render_data_yaml(root, names), encoding="utf-8")
    (root / "README.md").write_text(_render_dataset_readme(root, names), encoding="utf-8")
    return data_yaml_path


def train_answer_region_yolo(
    *,
    dataset_root: str | Path,
    model_path: str = "yolov8n.pt",
    epochs: int = 100,
    imgsz: int = 640,
    batch: int = 16,
    device: str = "cpu",
    project: str | Path = "runs/detect",
    name: str = "answer-region-yolo",
    class_names: Sequence[str] | None = None,
) -> dict[str, Any]:
    yolo_class = _resolve_yolo_class()
    if yolo_class is None:
        raise RuntimeError("ultralytics.YOLO is unavailable in the current environment")

    root = Path(dataset_root)
    names = _normalize_class_names(class_names)
    data_yaml_path = initialize_answer_region_dataset(root, class_names=names)
    model = yolo_class(model_path)
    train_results = model.train(
        data=str(data_yaml_path),
        epochs=int(epochs),
        imgsz=int(imgsz),
        batch=int(batch),
        device=str(device),
        project=str(project),
        name=str(name),
    )

    trainer = getattr(model, "trainer", None)
    save_dir = Path(getattr(trainer, "save_dir", Path(project) / name))
    best_weights_path = Path(getattr(trainer, "best", save_dir / "weights" / "best.pt"))
    return {
        "dataset_root": str(root),
        "data_yaml_path": str(data_yaml_path),
        "class_names": list(names),
        "save_dir": str(save_dir),
        "best_weights_path": str(best_weights_path),
        "train_results": train_results,
    }


def _resolve_yolo_class() -> Any | None:
    try:
        from ultralytics import YOLO
    except Exception:
        return None
    return YOLO


def _normalize_class_names(class_names: Sequence[str] | None) -> tuple[str, ...]:
    names = class_names or DEFAULT_ANSWER_REGION_CLASS_NAMES
    normalized = tuple(str(name).strip() for name in names if str(name).strip())
    if not normalized:
        raise ValueError("At least one YOLO class name is required")
    return normalized


def _render_data_yaml(dataset_root: Path, class_names: Sequence[str]) -> str:
    lines = [
        f"path: {dataset_root.as_posix()}",
        "train: images/train",
        "val: images/val",
        f"nc: {len(class_names)}",
        "names:",
    ]
    lines.extend(f"  - {name}" for name in class_names)
    lines.append("")
    return "\n".join(lines)


def _render_dataset_readme(dataset_root: Path, class_names: Sequence[str]) -> str:
    class_lines = "\n".join(f"- `{name}`" for name in class_names)
    return (
        "# Answer Region YOLO Dataset\n\n"
        "This dataset is organized for question-crop-based answer-region training.\n\n"
        "## Layout\n\n"
        f"- Root: `{dataset_root.as_posix()}`\n"
        "- Images: `images/train`, `images/val`\n"
        "- Labels: `labels/train`, `labels/val`\n"
        "- Config: `data.yaml`\n\n"
        "## Classes\n\n"
        f"{class_lines}\n\n"
        "Label each image using YOLO detection text files with normalized coordinates.\n"
    )
