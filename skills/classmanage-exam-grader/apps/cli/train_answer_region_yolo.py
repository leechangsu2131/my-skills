"""Train a YOLOv8 detector for question-crop answer-region localization."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from apps.cli.init_answer_region_yolo_dataset import DEFAULT_DATASET_ROOT
from packages.student_extraction.yolo_training import DEFAULT_ANSWER_REGION_CLASS_NAMES
from packages.student_extraction.yolo_training import train_answer_region_yolo


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Train a question-crop YOLOv8 detector for answer-region localization.",
    )
    parser.add_argument(
        "--dataset-root",
        default=str(DEFAULT_DATASET_ROOT),
        help="Dataset root containing images/, labels/, and data.yaml.",
    )
    parser.add_argument(
        "--model",
        default="yolov8n.pt",
        help="Base checkpoint to fine-tune. Default: yolov8n.pt",
    )
    parser.add_argument("--epochs", type=int, default=100, help="Training epochs. Default: 100")
    parser.add_argument("--imgsz", type=int, default=640, help="Training image size. Default: 640")
    parser.add_argument("--batch", type=int, default=16, help="Batch size. Default: 16")
    parser.add_argument("--device", default="cpu", help="Ultralytics device string. Default: cpu")
    parser.add_argument(
        "--project",
        default="runs/detect",
        help="Training output root. Default: runs/detect",
    )
    parser.add_argument(
        "--name",
        default="answer-region-yolo",
        help="Training run name. Default: answer-region-yolo",
    )
    parser.add_argument(
        "--class-name",
        dest="class_names",
        action="append",
        help="Repeat to override the default class list.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    class_names = tuple(args.class_names) if args.class_names else DEFAULT_ANSWER_REGION_CLASS_NAMES
    summary = train_answer_region_yolo(
        dataset_root=args.dataset_root,
        model_path=args.model,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        project=args.project,
        name=args.name,
        class_names=class_names,
    )
    print(f"Dataset: {Path(summary['data_yaml_path']).resolve()}")
    print(f"Run dir: {Path(summary['save_dir']).resolve()}")
    print(f"Best weights: {Path(summary['best_weights_path']).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
