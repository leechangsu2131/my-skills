import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import fitz

import schedule
import server


def make_pdf(path, pages):
    doc = fitz.open()
    for _ in range(pages):
        doc.new_page()
    doc.save(path)
    doc.close()


class ServerPdfTests(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()

    def test_pdf_endpoint_serves_pre_split_pdf_without_reslicing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            split_dir = Path(tmpdir) / "pdf_splits"
            split_dir.mkdir()
            pdf_path = split_dir / "[social]_subunit_08_intro_p55-62.pdf"
            make_pdf(pdf_path, 8)

            record = {
                schedule.COLUMN_SUBJECT: "사회",
                schedule.COLUMN_LESSON: "11",
                schedule.COLUMN_PDF: str(pdf_path),
                schedule.COLUMN_START_PAGE: "55",
                schedule.COLUMN_END_PAGE: "62",
            }

            with (
                patch.object(server.schedule, "connect", return_value=object()),
                patch.object(server.schedule, "load_all", return_value=[record]),
                patch.object(server.schedule, "find_record_by_key", return_value=record),
            ):
                response = self.client.get("/api/pdf/lesson-0194")

            self.assertEqual(response.status_code, 200)
            served = fitz.open(stream=response.data, filetype="pdf")
            self.assertEqual(len(served), 8)
            served.close()
            response.close()

    def test_pdf_endpoint_still_slices_regular_pdf_by_page_range(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "book.pdf"
            make_pdf(pdf_path, 5)

            record = {
                schedule.COLUMN_SUBJECT: "사회",
                schedule.COLUMN_LESSON: "11",
                schedule.COLUMN_PDF: str(pdf_path),
                schedule.COLUMN_START_PAGE: "2",
                schedule.COLUMN_END_PAGE: "4",
            }

            with (
                patch.object(server.schedule, "connect", return_value=object()),
                patch.object(server.schedule, "load_all", return_value=[record]),
                patch.object(server.schedule, "find_record_by_key", return_value=record),
            ):
                response = self.client.get("/api/pdf/lesson-0194")

            self.assertEqual(response.status_code, 200)
            served = fitz.open(stream=response.data, filetype="pdf")
            self.assertEqual(len(served), 3)
            served.close()
            response.close()


if __name__ == "__main__":
    unittest.main()
