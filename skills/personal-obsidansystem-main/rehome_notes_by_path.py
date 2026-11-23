"""Rehome Obsidian notes based on their frontmatter `path` property."""

from __future__ import annotations

import argparse
from pathlib import Path

from pkm_core import (
    get_current_props,
    move_note_to_path_prop,
    resolve_note_target_dir_from_path_value,
)


EXCLUDED_PARTS = {
    "_PKM_BACKUP",
    "knowledge",
    "daily",
    "Clippings",
    "reports",
    ".obsidian",
    ".trash",
    ".space",
    ".makemd",
    ".smart-env",
}


def iter_candidate_notes(vault_path: Path) -> list[Path]:
    notes: list[Path] = []
    for note_path in vault_path.rglob("*.md"):
        rel_parts = note_path.relative_to(vault_path).parts
        if any(part in EXCLUDED_PARTS for part in rel_parts):
            continue
        notes.append(note_path)
    return sorted(notes)


def resolve_selected_notes(vault_path: Path, args) -> list[Path]:
    if args.all:
        return [
            note_path
            for note_path in iter_candidate_notes(vault_path)
            if get_current_props(note_path).get("path")
        ]

    selected: list[Path] = []
    for rel in args.note or []:
        candidate = (vault_path / rel).resolve()
        if not candidate.exists():
            raise FileNotFoundError(f"note not found: {rel}")
        selected.append(candidate)
    return selected


def dry_run(notes: list[Path], vault_path: Path) -> int:
    moved = skipped = conflict = error = 0
    for note_path in notes:
        props = get_current_props(note_path)
        path_value = props.get("path", "")
        rel = note_path.relative_to(vault_path).as_posix()
        if not path_value:
            print(f"SKIP     {rel} :: no path property")
            skipped += 1
            continue
        try:
            target_dir = resolve_note_target_dir_from_path_value(vault_path, str(path_value))
            destination = (target_dir / note_path.name).resolve()
            if destination == note_path.resolve():
                print(f"SKIP     {rel} :: already in place")
                skipped += 1
            elif destination.exists():
                print(
                    f"CONFLICT {rel} -> "
                    f"{destination.relative_to(vault_path).as_posix()} :: destination exists"
                )
                conflict += 1
            else:
                print(
                    f"MOVE     {rel} -> "
                    f"{destination.relative_to(vault_path).as_posix()}"
                )
                moved += 1
        except Exception as exc:  # pragma: no cover - defensive CLI path
            print(f"ERROR    {rel} :: {exc}")
            error += 1

    print(
        f"\nSummary: move {moved} / skip {skipped} / conflict {conflict} / error {error}"
    )
    return 0 if error == 0 else 1


def apply(notes: list[Path], vault_path: Path) -> int:
    moved = skipped = conflict = error = 0
    for note_path in notes:
        rel = note_path.relative_to(vault_path).as_posix()
        status, destination, detail = move_note_to_path_prop(note_path, vault_path)
        if status == "moved":
            moved += 1
            print(
                f"MOVED    {rel} -> {destination.relative_to(vault_path).as_posix()}"
            )
        elif status == "skipped":
            skipped += 1
            print(f"SKIP     {rel} :: {detail}")
        elif status == "conflict":
            conflict += 1
            target = destination.relative_to(vault_path).as_posix() if destination else detail
            print(f"CONFLICT {rel} -> {target}")
        else:
            error += 1
            print(f"ERROR    {rel} :: {detail}")

    print(
        f"\nSummary: moved {moved} / skipped {skipped} / conflict {conflict} / error {error}"
    )
    return 0 if error == 0 else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Move notes into the folder declared by their frontmatter path property.",
    )
    parser.add_argument("vault", help="Obsidian vault path")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process every markdown file that currently has a path property.",
    )
    parser.add_argument(
        "--note",
        action="append",
        default=[],
        help="Relative note path inside the vault. Repeat for multiple files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview moves without changing files.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    vault_path = Path(args.vault).resolve()
    if not vault_path.exists():
        parser.error(f"vault does not exist: {vault_path}")
    if not args.all and not args.note:
        parser.error("choose --all or provide at least one --note")

    notes = resolve_selected_notes(vault_path, args)
    if not notes:
        print("No matching notes found.")
        return 0

    if args.dry_run:
        return dry_run(notes, vault_path)
    return apply(notes, vault_path)


if __name__ == "__main__":
    raise SystemExit(main())
