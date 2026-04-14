import argparse
import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sheet_uploader.core import (
    REPLACE_ALL,
    REPLACE_APPEND,
    REPLACE_SUBJECTS,
    upload_rows_to_sheet,
)


DEFAULT_ROWS_PATH = ROOT_DIR / "generated_rows" / "latest_all_rows.json"


def load_rows(rows_path):
    data = json.loads(Path(rows_path).read_text(encoding="utf-8"))
    if isinstance(data, dict) and "rows" in data:
        return data["rows"]
    if isinstance(data, list):
        return data
    raise ValueError("rows json format is not supported")


def main():
    parser = argparse.ArgumentParser(description="\uc0dd\uc131\ub41c \uc9c4\ub3c4\ud45c json\uc744 \uad6c\uae00 \uc2dc\ud2b8\uc5d0 \uc5c5\ub85c\ub4dc")
    parser.add_argument(
        "--rows-json",
        default=str(DEFAULT_ROWS_PATH),
        help="\uc5c5\ub85c\ub4dc\ud560 rows json \uacbd\ub85c",
    )
    parser.add_argument("--cleanup", action="store_true", help="\uc5c5\ub85c\ub4dc \uc804 \uc911\ubcf5 \ud589 \uc0ad\uc81c")
    parser.add_argument("--replace-subjects", action="store_true", help="\uc5c5\ub85c\ub4dc\ud560 \uacfc\ubaa9\uc758 \uae30\uc874 \ud589\uc744 \uc9c0\uc6b0\uace0 \uc5c5\ub85c\ub4dc")
    parser.add_argument("--replace-all", action="store_true", help="\uc9c4\ub3c4\ud45c\uc758 \uae30\uc874 \ud589 \uc804\uccb4\ub97c \uc9c0\uc6b0\uace0 \uc5c5\ub85c\ub4dc")
    args = parser.parse_args()

    if args.replace_subjects and args.replace_all:
        parser.error("--replace-subjects\uc640 --replace-all\uc740 \uac19\uc774 \uc0ac\uc6a9\ud560 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4.")

    rows = load_rows(args.rows_json)
    print(f"[\uc900\ube44] {len(rows)}\ud589 \ub85c\ub4dc: {args.rows_json}")
    replace_mode = REPLACE_APPEND
    if args.replace_all:
        replace_mode = REPLACE_ALL
    elif args.replace_subjects:
        replace_mode = REPLACE_SUBJECTS
    upload_rows_to_sheet(rows, cleanup=args.cleanup, replace_mode=replace_mode)


if __name__ == "__main__":
    main()
