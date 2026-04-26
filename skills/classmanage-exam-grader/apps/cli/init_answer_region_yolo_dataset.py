"""Initialize a local question-crop YOLO dataset for answer-region training."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from packages.student_extraction.yolo_training import DEFAULT_ANSWER_REGION_CLASS_NAMES
from packages.student_extraction.yolo_training import initialize_answer_region_dataset


DEFAULT_DATASET_ROOT = Path("data/yolo_answer_regions")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create the local question-crop YOLO dataset folders for answer-region training.",
    )
    parser.add_argument(
        "--dataset-root",
        default=str(DEFAULT_DATASET_ROOT),
        help="Target dataset root. Default: data/yolo_answer_regions",
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
    data_yaml_path = initialize_answer_region_dataset(
        args.dataset_root,
        class_names=class_names,
    )
    print(f"Initialized YOLO dataset at {Path(args.dataset_root).resolve()}")
    print(f"data.yaml: {data_yaml_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
