from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from packages.student_extraction.yolo_training import DEFAULT_ANSWER_REGION_CLASS_NAMES
from packages.student_extraction.yolo_training import initialize_answer_region_dataset
from packages.student_extraction.yolo_training import train_answer_region_yolo


def test_initialize_answer_region_dataset_creates_expected_layout(tmp_path: Path) -> None:
    dataset_root = tmp_path / "dataset"

    data_yaml_path = initialize_answer_region_dataset(dataset_root)

    assert data_yaml_path == dataset_root / "data.yaml"
    assert (dataset_root / "images" / "train").is_dir()
    assert (dataset_root / "images" / "val").is_dir()
    assert (dataset_root / "labels" / "train").is_dir()
    assert (dataset_root / "labels" / "val").is_dir()
    assert (dataset_root / "README.md").is_file()

    data_yaml_text = data_yaml_path.read_text(encoding="utf-8")
    assert f"path: {dataset_root.as_posix()}" in data_yaml_text
    assert "train: images/train" in data_yaml_text
    assert "val: images/val" in data_yaml_text
    assert "nc: 3" in data_yaml_text
    assert "choice_answer_region" in data_yaml_text
    assert "short_answer_line" in data_yaml_text
    assert "descriptive_answer_area" in data_yaml_text


def test_train_answer_region_yolo_uses_generated_dataset_yaml(monkeypatch, tmp_path: Path) -> None:
    dataset_root = tmp_path / "dataset"
    project_root = tmp_path / "runs"
    recorded: dict[str, object] = {}

    class FakeYolo:
        def __init__(self, weights_path: str) -> None:
            recorded["weights_path"] = weights_path
            self.trainer = SimpleNamespace(
                save_dir=project_root / "answer-region-smoke",
                best=project_root / "answer-region-smoke" / "weights" / "best.pt",
            )

        def train(self, **kwargs: object) -> dict[str, float]:
            recorded["train_kwargs"] = kwargs
            return {"metrics/mAP50(B)": 0.91}

    monkeypatch.setattr(
        "packages.student_extraction.yolo_training._resolve_yolo_class",
        lambda: FakeYolo,
    )

    summary = train_answer_region_yolo(
        dataset_root=dataset_root,
        model_path="yolov8n.pt",
        epochs=3,
        imgsz=512,
        batch=4,
        device="cpu",
        project=project_root,
        name="answer-region-smoke",
    )

    assert recorded["weights_path"] == "yolov8n.pt"
    train_kwargs = recorded["train_kwargs"]
    assert train_kwargs["data"] == str(dataset_root / "data.yaml")
    assert train_kwargs["epochs"] == 3
    assert train_kwargs["imgsz"] == 512
    assert train_kwargs["batch"] == 4
    assert train_kwargs["device"] == "cpu"
    assert train_kwargs["project"] == str(project_root)
    assert train_kwargs["name"] == "answer-region-smoke"
    assert summary["class_names"] == list(DEFAULT_ANSWER_REGION_CLASS_NAMES)
    assert summary["data_yaml_path"] == str(dataset_root / "data.yaml")
    assert summary["best_weights_path"] == str(project_root / "answer-region-smoke" / "weights" / "best.pt")
