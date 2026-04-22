"""Thin app-layer entrypoint for the web UI."""

from webapp.main import app
from webapp.main import create_app

__all__ = ["app", "create_app"]
