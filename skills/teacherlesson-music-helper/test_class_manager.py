import unittest
from pathlib import Path
from uuid import uuid4

import class_manager


class ClassManagerTests(unittest.TestCase):
    def setUp(self):
        self.storage_path = Path(__file__).parent / f"test_data_{uuid4().hex}.json"

    def tearDown(self):
        self.storage_path.unlink(missing_ok=True)

    def test_add_and_get_saved_class(self):
        class_manager.add_saved_class(
            "3학년 1단원",
            "1단원",
            "1~2차시",
            pdf_path="C:/pdf/music.pdf",
            storage_path=self.storage_path,
        )

        saved = class_manager.get_saved_class("3학년 1단원", storage_path=self.storage_path)

        self.assertIsNotNone(saved)
        self.assertEqual(saved["unit"], "1단원")
        self.assertEqual(saved["lesson"], "1~2차시")
        self.assertEqual(saved["pdf_path"], "C:/pdf/music.pdf")
        self.assertEqual(saved["exact_title"], "")

    def test_add_saved_class_with_exact_title(self):
        class_manager.add_saved_class(
            "3학년 1단원",
            "1단원",
            "1~2차시",
            pdf_path="C:/pdf/music.pdf",
            exact_title="[1~2차시] 새 친구들과 함께",
            storage_path=self.storage_path,
        )

        saved = class_manager.get_saved_class("3학년 1단원", storage_path=self.storage_path)

        self.assertEqual(saved["exact_title"], "[1~2차시] 새 친구들과 함께")

    def test_delete_saved_class(self):
        class_manager.add_saved_class("테스트", "2단원", "3차시", storage_path=self.storage_path)

        deleted = class_manager.delete_saved_class("테스트", storage_path=self.storage_path)

        self.assertTrue(deleted)
        self.assertIsNone(class_manager.get_saved_class("테스트", storage_path=self.storage_path))

    def test_update_saved_class(self):
        class_manager.add_saved_class("테스트", "2단원", "3차시", storage_path=self.storage_path)

        updated = class_manager.update_saved_class(
            "테스트",
            lesson="[5~6차시] 구슬비",
            exact_title="[5~6차시] 구슬비",
            storage_path=self.storage_path,
        )

        self.assertIsNotNone(updated)
        self.assertEqual(updated["lesson"], "[5~6차시] 구슬비")
        self.assertEqual(updated["exact_title"], "[5~6차시] 구슬비")

    def test_recent_runs_are_limited(self):
        for index in range(12):
            class_manager.record_recent_run(
                unit=f"{index}단원",
                lesson=f"{index}차시",
                storage_path=self.storage_path,
                limit=10,
            )

        recent_runs = class_manager.list_recent_runs(storage_path=self.storage_path)

        self.assertEqual(len(recent_runs), 10)
        self.assertEqual(recent_runs[0]["unit"], "11단원")
        self.assertEqual(recent_runs[-1]["unit"], "2단원")


if __name__ == "__main__":
    unittest.main()
