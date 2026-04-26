from apps.cli import grade_exam as cli_entry
from apps.cli import init_answer_region_yolo_dataset as init_yolo_entry
from apps.cli import train_answer_region_yolo as train_yolo_entry
from apps.web import main as web_entry


def test_web_app_entrypoint_matches_existing_webapp_module() -> None:
    import webapp.main

    assert web_entry.create_app is webapp.main.create_app
    assert web_entry.app is webapp.main.app


def test_cli_entrypoint_matches_existing_grade_exam_module() -> None:
    import grade_exam

    assert cli_entry.main is grade_exam.main


def test_init_yolo_dataset_cli_creates_default_scaffold(tmp_path, capsys) -> None:
    dataset_root = tmp_path / "dataset"

    exit_code = init_yolo_entry.main(["--dataset-root", str(dataset_root)])

    assert exit_code == 0
    assert (dataset_root / "data.yaml").is_file()
    assert "Initialized YOLO dataset" in capsys.readouterr().out


def test_train_yolo_cli_forwards_arguments(monkeypatch, tmp_path, capsys) -> None:
    recorded: dict[str, object] = {}

    def fake_train_answer_region_yolo(**kwargs):
        recorded.update(kwargs)
        run_root = tmp_path / "runs" / "smoke"
        return {
            "data_yaml_path": str(tmp_path / "dataset" / "data.yaml"),
            "save_dir": str(run_root),
            "best_weights_path": str(run_root / "weights" / "best.pt"),
        }

    monkeypatch.setattr(train_yolo_entry, "train_answer_region_yolo", fake_train_answer_region_yolo)

    exit_code = train_yolo_entry.main(
        [
            "--dataset-root",
            str(tmp_path / "dataset"),
            "--model",
            "yolov8n.pt",
            "--epochs",
            "5",
            "--imgsz",
            "768",
            "--batch",
            "2",
            "--device",
            "cpu",
            "--project",
            str(tmp_path / "runs"),
            "--name",
            "smoke",
        ]
    )

    assert exit_code == 0
    assert recorded["dataset_root"] == str(tmp_path / "dataset")
    assert recorded["model_path"] == "yolov8n.pt"
    assert recorded["epochs"] == 5
    assert recorded["imgsz"] == 768
    assert recorded["batch"] == 2
    assert recorded["device"] == "cpu"
    assert recorded["project"] == str(tmp_path / "runs")
    assert recorded["name"] == "smoke"
    assert "Best weights:" in capsys.readouterr().out
