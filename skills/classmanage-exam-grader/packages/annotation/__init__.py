"""Annotation output package."""

from packages.annotation.service import annotate_batch
from packages.annotation.service import annotate_pdf
from packages.annotation.service import create_summary_page
from packages.annotation.service import load_config
from packages.annotation.service import stamp_first_page

__all__ = [
    "annotate_batch",
    "annotate_pdf",
    "create_summary_page",
    "load_config",
    "stamp_first_page",
]
