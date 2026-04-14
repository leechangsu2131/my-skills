import unittest
from pathlib import Path
from uuid import uuid4

import social_class_store


class SocialClassStoreTests(unittest.TestCase):
    def setUp(self):
        self.storage_path = Path(__file__).parent / f"test_data_{uuid4().hex}.json"

    def tearDown(self):
        self.storage_path.unlink(missing_ok=True)

    def test_upsert_and_get_saved_lesson(self):
        social_class_store.upsert_saved_lesson(
            "3학년 1단원",
            "1단원",
            "1~2차시",
            exact_title="[1~2차시] 우리 지역의 위치",
            guide_pdf_path="C:/guides/social-guide.pdf",
            storage_path=self.storage_path,
        )

        saved = social_class_store.get_saved_lesson("3학년 1단원", storage_path=self.storage_path)

        self.assertIsNotNone(saved)
        self.assertEqual(saved["unit"], "1단원")
        self.assertEqual(saved["lesson"], "1~2차시")
        self.assertEqual(saved["exact_title"], "[1~2차시] 우리 지역의 위치")
        self.assertEqual(saved["guide_pdf_path"], "C:/guides/social-guide.pdf")

    def test_delete_saved_lesson(self):
        social_class_store.upsert_saved_lesson(
            "테스트",
            "2단원",
            "3차시",
            storage_path=self.storage_path,
        )

        deleted = social_class_store.delete_saved_lesson("테스트", storage_path=self.storage_path)

        self.assertTrue(deleted)
        self.assertIsNone(
            social_class_store.get_saved_lesson("테스트", storage_path=self.storage_path)
        )

    def test_upsert_preserves_existing_guide_pdf_path_when_blank(self):
        social_class_store.upsert_saved_lesson(
            "3학년 1단원",
            "1단원",
            "1~2차시",
            guide_pdf_path="C:/guides/social-guide.pdf",
            storage_path=self.storage_path,
        )

        social_class_store.upsert_saved_lesson(
            "3학년 1단원",
            "1단원",
            "1~2차시",
            storage_path=self.storage_path,
        )

        saved = social_class_store.get_saved_lesson("3학년 1단원", storage_path=self.storage_path)
        self.assertEqual(saved["guide_pdf_path"], "C:/guides/social-guide.pdf")

    def test_recent_runs_are_limited(self):
        for index in range(12):
            social_class_store.record_recent_run(
                unit=f"{index}단원",
                lesson=f"{index}차시",
                storage_path=self.storage_path,
                limit=10,
            )

        recent_runs = social_class_store.list_recent_runs(storage_path=self.storage_path)

        self.assertEqual(len(recent_runs), 10)
        self.assertEqual(recent_runs[0]["unit"], "11단원")
        self.assertEqual(recent_runs[-1]["unit"], "2단원")


if __name__ == "__main__":
    unittest.main()
