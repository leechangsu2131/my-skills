"""Thin package boundary for PDF annotation output."""

from pdf_annotator import annotate_batch
from pdf_annotator import annotate_pdf
from pdf_annotator import create_summary_page
from pdf_annotator import load_config
from pdf_annotator import stamp_first_page

__all__ = [
    "annotate_batch",
    "annotate_pdf",
    "create_summary_page",
    "load_config",
    "stamp_first_page",
]
