import unittest
from unittest.mock import patch

from sheet_uploader import core


class FakeWorksheet:
    def __init__(self, rows):
        self.rows = [list(row) for row in rows]

    def row_values(self, index):
        return list(self.rows[index - 1])

    def get_all_values(self):
        return [list(row) for row in self.rows]

    def get_all_records(self, default_blank=""):
        headers = self.rows[0]
        records = []
        for row in self.rows[1:]:
            padded = list(row) + [default_blank] * max(0, len(headers) - len(row))
            records.append(
                {
                    str(header).strip(): (padded[idx] if idx < len(padded) else default_blank)
                    for idx, header in enumerate(headers)
                    if str(header).strip()
                }
            )
        return records

    def delete_rows(self, start, end=None):
        end = start if end is None else end
        del self.rows[start - 1 : end]

    def append_rows(self, new_rows, value_input_option=None):
        del value_input_option
        self.rows.extend([list(row) for row in new_rows])


class SheetUploaderCoreTests(unittest.TestCase):
    def test_upload_rows_to_sheet_replace_subjects_deletes_matching_subject_rows(self):
        ws = FakeWorksheet(
            [
                ["과목", "차시", "수업내용", "대단원", "계획일", "실행여부"],
                ["국어", "1", "기존 국어", "1단원", "", ""],
                ["미술", "1", "기존 미술", "1단원", "", ""],
                ["사회", "1", "기존 사회", "1단원", "", ""],
            ]
        )
        rows = [
            {
                "과목": "미술",
                "차시": "2",
                "수업내용": "새 미술",
                "대단원": "1단원",
                "계획일": "",
                "실행여부": False,
            }
        ]

        with patch.object(core, "get_sheet", return_value=(None, ws)):
            uploaded = core.upload_rows_to_sheet(rows, replace_mode=core.REPLACE_SUBJECTS, print_fn=lambda *_a, **_k: None)

        self.assertEqual(uploaded, 1)
        self.assertEqual([row[0] for row in ws.rows[1:]], ["국어", "사회", "미술"])
        self.assertEqual(ws.rows[-1][:4], ["미술", "2", "새 미술", "1단원"])

    def test_upload_rows_to_sheet_replace_all_clears_existing_rows(self):
        ws = FakeWorksheet(
            [
                ["과목", "차시", "수업내용", "대단원", "계획일", "실행여부"],
                ["국어", "1", "기존 국어", "1단원", "", ""],
                ["미술", "1", "기존 미술", "1단원", "", ""],
            ]
        )
        rows = [
            {
                "과목": "음악",
                "차시": "3",
                "수업내용": "새 음악",
                "대단원": "1단원",
                "계획일": "",
                "실행여부": False,
            }
        ]

        with patch.object(core, "get_sheet", return_value=(None, ws)):
            uploaded = core.upload_rows_to_sheet(rows, replace_mode=core.REPLACE_ALL, print_fn=lambda *_a, **_k: None)

        self.assertEqual(uploaded, 1)
        self.assertEqual(len(ws.rows), 2)
        self.assertEqual(ws.rows[1][:4], ["음악", "3", "새 음악", "1단원"])


if __name__ == "__main__":
    unittest.main()
