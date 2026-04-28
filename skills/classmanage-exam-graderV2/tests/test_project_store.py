import json
import tempfile
import unittest
from pathlib import Path

import sys


BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))

from project_store import (  # type: ignore
    create_project,
    load_settings,
    project_paths,
    refresh_project_metadata,
    save_settings,
    slugify_project_name,
)


class ProjectStoreTests(unittest.TestCase):
    def test_load_settings_creates_default_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "settings.json"

            settings = load_settings(settings_path)

            self.assertTrue(settings_path.exists())
            self.assertIn("root_dir", settings)
            self.assertEqual(settings["app_version"], "2.0")

    def test_create_project_initializes_expected_structure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root_dir = Path(tmp) / "projects"
            settings_path = Path(tmp) / "settings.json"
            save_settings(settings_path, {"root_dir": str(root_dir), "last_project": None})

            project = create_project(
                root_dir,
                {
                    "name": "3학년 2반 수학 1단원",
                    "grade": "3학년",
                    "class": "2반",
                    "subject": "수학",
                    "exam_name": "1단원 평가",
                },
            )

            project_dir = root_dir / project["slug"]
            paths = project_paths(project_dir)

            self.assertTrue(paths.project_json.exists())
            self.assertTrue(paths.template_dir.is_dir())
            self.assertTrue(paths.answers_dir.is_dir())
            self.assertTrue(paths.student_pdf_dir.is_dir())
            self.assertTrue(paths.student_page_dir.is_dir())
            self.assertTrue(paths.aligned_dir.is_dir())
            self.assertTrue(paths.json_dir.is_dir())
            self.assertTrue(paths.yolo_dir.is_dir())
            self.assertTrue(paths.logs_dir.is_dir())

            saved = json.loads(paths.project_json.read_text(encoding="utf-8"))
            self.assertEqual(saved["name"], "3학년 2반 수학 1단원")
            self.assertEqual(saved["status"]["template_ready"], False)
            self.assertEqual(saved["status"]["review_done"], False)

    def test_refresh_project_metadata_updates_counts_and_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            root_dir = Path(tmp) / "projects"
            project = create_project(
                root_dir,
                {
                    "name": "3학년 2반 수학 1단원",
                    "grade": "3학년",
                    "class": "2반",
                    "subject": "수학",
                    "exam_name": "1단원 평가",
                },
            )
            project_dir = root_dir / project["slug"]
            paths = project_paths(project_dir)

            (paths.template_dir / "blank_p1.png").write_bytes(b"1")
            (paths.template_dir / "blank_p2.png").write_bytes(b"2")
            (paths.answers_dir / "answer_key.pdf").write_bytes(b"pdf")
            (paths.student_pdf_dir / "bundle.pdf").write_bytes(b"pdf")
            (paths.student_page_dir / "exam_stu001_p1.jpg").write_bytes(b"img")
            (paths.student_page_dir / "exam_stu001_p2.jpg").write_bytes(b"img")
            (paths.student_page_dir / "exam_stu002_p1.jpg").write_bytes(b"img")
            (paths.aligned_dir / "aligned_exam_stu001_p1.jpg").write_bytes(b"img")
            (paths.aligned_dir / "aligned_exam_stu001_p2.jpg").write_bytes(b"img")
            (paths.aligned_dir / "aligned_exam_stu002_p1.jpg").write_bytes(b"img")
            (paths.json_dir / "regions.json").write_text(
                json.dumps({"questions": [{"page": 1}, {"page": 1}, {"page": 2}]}, ensure_ascii=False),
                encoding="utf-8",
            )
            (paths.yolo_dir / "aligned_exam_stu001_p1.txt").write_text("0 0.5 0.5 0.1 0.1", encoding="utf-8")

            project_info = refresh_project_metadata(project_dir)

            self.assertEqual(project_info["template_pages"], 2)
            self.assertEqual(project_info["total_questions"], 3)
            self.assertEqual(project_info["student_count"], 2)
            self.assertTrue(project_info["status"]["template_ready"])
            self.assertTrue(project_info["status"]["regions_ready"])
            self.assertTrue(project_info["status"]["alignment_done"])
            self.assertTrue(project_info["status"]["review_done"])

    def test_slugify_replaces_spaces_and_invalid_chars(self):
        self.assertEqual(
            slugify_project_name("3학년 2반: 수학 / 1단원"),
            "3학년_2반_수학_1단원",
        )


if __name__ == "__main__":
    unittest.main()
