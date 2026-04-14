import shutil
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import fitz

import schedule
import server


TEST_TMP_ROOT = Path(__file__).resolve().parents[1] / ".tmp-tests"


def make_pdf(path, pages):
    doc = fitz.open()
    for _ in range(pages):
        doc.new_page()
    doc.save(path)
    doc.close()


@contextmanager
def make_temp_dir():
    TEST_TMP_ROOT.mkdir(exist_ok=True)
    path = TEST_TMP_ROOT / f"tmp-{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield str(path)
    finally:
        shutil.rmtree(path, ignore_errors=True)


class ServerPdfTests(unittest.TestCase):
    def setUp(self):
        server._clear_dashboard_cache()
        self.client = server.app.test_client()

    def test_pdf_endpoint_serves_pre_split_pdf_without_reslicing(self):
        with make_temp_dir() as tmpdir:
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
        with make_temp_dir() as tmpdir:
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

    def test_pdf_endpoint_serves_whole_pdf_when_page_range_is_missing(self):
        with make_temp_dir() as tmpdir:
            pdf_path = Path(tmpdir) / "korean-fragment.pdf"
            make_pdf(pdf_path, 6)

            record = {
                schedule.COLUMN_SUBJECT: "국어",
                schedule.COLUMN_LESSON: "11",
                schedule.COLUMN_PDF: str(pdf_path),
                schedule.COLUMN_START_PAGE: "",
                schedule.COLUMN_END_PAGE: "",
            }

            with (
                patch.object(server.schedule, "connect", return_value=object()),
                patch.object(server.schedule, "load_all", return_value=[record]),
                patch.object(server.schedule, "find_record_by_key", return_value=record),
            ):
                response = self.client.get("/api/pdf/lesson-0194")

            self.assertEqual(response.status_code, 200)
            served = fitz.open(stream=response.data, filetype="pdf")
            self.assertEqual(len(served), 6)
            served.close()
            response.close()

    def test_pdf_endpoint_serves_whole_pdf_when_stored_file_is_already_trimmed(self):
        with make_temp_dir() as tmpdir:
            pdf_path = Path(tmpdir) / "korean-lesson.pdf"
            make_pdf(pdf_path, 8)

            record = {
                schedule.COLUMN_SUBJECT: "국어",
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


class ServerDashboardCacheTests(unittest.TestCase):
    def setUp(self):
        server._clear_dashboard_cache()
        self.client = server.app.test_client()

    def tearDown(self):
        server._clear_dashboard_cache()

    def test_dashboard_reuses_cached_payload_within_ttl(self):
        calls = []

        def fake_build(board_date=None):
            calls.append(board_date.isoformat() if board_date else "default")
            return {
                "views": [],
                "subjects": [],
                "board_date": board_date.isoformat() if board_date else "",
                "today": "2026-04-04",
                "generation": len(calls),
            }

        with (
            patch.object(server, "DASHBOARD_CACHE_TTL_SECONDS", 3),
            patch.object(server, "_build_dashboard_payload", side_effect=fake_build),
        ):
            with patch.object(server, "_cache_now", return_value=100.0):
                first = server._dashboard_payload()
            with patch.object(server, "_cache_now", return_value=101.0):
                second = server._dashboard_payload()

        self.assertEqual(first["generation"], 1)
        self.assertEqual(second["generation"], 1)
        self.assertEqual(calls, ["default"])

    def test_dashboard_cache_expires_after_ttl(self):
        calls = []

        def fake_build(board_date=None):
            calls.append(board_date.isoformat() if board_date else "default")
            return {
                "views": [],
                "subjects": [],
                "board_date": board_date.isoformat() if board_date else "",
                "today": "2026-04-04",
                "generation": len(calls),
            }

        with (
            patch.object(server, "DASHBOARD_CACHE_TTL_SECONDS", 3),
            patch.object(server, "_build_dashboard_payload", side_effect=fake_build),
        ):
            with patch.object(server, "_cache_now", return_value=100.0):
                first = server._dashboard_payload()
            with patch.object(server, "_cache_now", return_value=101.0):
                second = server._dashboard_payload()
            with patch.object(server, "_cache_now", return_value=104.5):
                third = server._dashboard_payload()

        self.assertEqual(first["generation"], 1)
        self.assertEqual(second["generation"], 1)
        self.assertEqual(third["generation"], 2)
        self.assertEqual(calls, ["default", "default"])

    def test_write_actions_invalidate_dashboard_cache(self):
        calls = []

        def fake_build(board_date=None):
            calls.append(board_date.isoformat() if board_date else "default")
            return {
                "views": [],
                "subjects": [],
                "board_date": board_date.isoformat() if board_date else "",
                "today": "2026-04-04",
                "generation": len(calls),
            }

        with (
            patch.object(server, "DASHBOARD_CACHE_TTL_SECONDS", 3),
            patch.object(server, "_build_dashboard_payload", side_effect=fake_build),
            patch.object(server.schedule, "connect", return_value=object()),
            patch.object(server.schedule, "load_all", return_value=[]),
            patch.object(server.schedule, "push_schedule", return_value={"message": "ok"}),
            patch.object(server, "log_action"),
        ):
            with patch.object(server, "_cache_now", return_value=100.0):
                first = server._dashboard_payload()
            action = self.client.post("/api/push", json={"subject": "국어", "days": 3})
            with patch.object(server, "_cache_now", return_value=101.0):
                second = server._dashboard_payload()

        self.assertEqual(action.status_code, 200)
        self.assertEqual(first["generation"], 1)
        self.assertEqual(second["generation"], 2)
        self.assertEqual(calls, ["default", "default"])


if __name__ == "__main__":
    unittest.main()
