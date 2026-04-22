"""Thin app-layer entrypoint for the CLI workflow."""

from grade_exam import main

__all__ = ["main"]


if __name__ == "__main__":
    raise SystemExit(main())
