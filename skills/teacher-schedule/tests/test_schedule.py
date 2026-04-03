import re
import unittest
from datetime import date

import bridge_sheet
import schedule


class WorksheetNotFound(Exception):
    pass


class FakeSpreadsheet:
    def __init__(self, worksheets=None):
        self.worksheets = {}
        self.batch_updates = []
        if worksheets:
            for worksheet in worksheets:
                self.attach(worksheet)

    def attach(self, worksheet):
        worksheet.spreadsheet = self
        self.worksheets[worksheet.title] = worksheet
        return worksheet

    def worksheet(self, title):
        worksheet = self.worksheets.get(title)
        if worksheet is None:
            raise WorksheetNotFound(title)
        return worksheet

    def add_worksheet(self, title, rows=1000, cols=1):
        worksheet = FakeWorksheet([""] * cols, [], title=title, spreadsheet=self)
        return worksheet

    @staticmethod
    def _column_to_index(text):
        value = 0
        for char in text:
            value = value * 26 + (ord(char) - 64)
        return value

    @staticmethod
    def _parse_range(a1_range):
        match = re.match(r"^(?:(.+)!)?([A-Z]+)(\d+)(?::([A-Z]+)(\d+))?$", a1_range)
        if not match:
            raise ValueError(f"Unsupported range: {a1_range}")
        sheet_name, start_col, start_row, end_col, end_row = match.groups()
        return {
            "sheet_name": sheet_name,
            "start_col": FakeSpreadsheet._column_to_index(start_col),
            "start_row": int(start_row),
            "end_col": FakeSpreadsheet._column_to_index(end_col) if end_col else None,
            "end_row": int(end_row) if end_row else None,
        }

    def values_batch_update(self, payload):
        self.batch_updates.append(payload)
        for update in payload.get("data", []):
            parsed = self._parse_range(update.get("range", ""))
            worksheet = self.worksheet(parsed["sheet_name"])
            values = update.get("values", [])
            for row_offset, row_values in enumerate(values):
                for col_offset, value in enumerate(row_values):
                    worksheet.set_cell(
                        parsed["start_row"] + row_offset,
                        parsed["start_col"] + col_offset,
                        value,
                    )


class FakeWorksheet:
    def __init__(self, headers, rows, title=None, spreadsheet=None):
        self.headers = list(headers)
        self.rows = [list(row) for row in rows]
        self.title = title or schedule.SHEET_NAME
        self.spreadsheet = None
        if spreadsheet is None:
            spreadsheet = FakeSpreadsheet()
        spreadsheet.attach(self)

    def _ensure_size(self, row_number, col_number):
        while len(self.headers) < col_number:
            self.headers.append("")
            for row in self.rows:
                row.append("")
        while len(self.rows) < max(0, row_number - 1):
            self.rows.append([""] * len(self.headers))
        if row_number >= 2:
            row = self.rows[row_number - 2]
            while len(row) < len(self.headers):
                row.append("")

    def set_cell(self, row_number, col_number, value):
        self._ensure_size(row_number, col_number)
        if row_number == 1:
            self.headers[col_number - 1] = value
            return
        self.rows[row_number - 2][col_number - 1] = value

    def row_values(self, index):
        if index == 1:
            return self.headers[:]
        row_index = index - 2
        if 0 <= row_index < len(self.rows):
            row = self.rows[row_index]
            return row + [""] * max(0, len(self.headers) - len(row))
        return []

    def get_all_records(self, default_blank=""):
        records = []
        for row in self.rows:
            expanded = row + [default_blank] * max(0, len(self.headers) - len(row))
            records.append(
                {
                    header: expanded[index]
                    for index, header in enumerate(self.headers)
                }
            )
        return records

    def get_all_values(self):
        values = [self.headers[:]]
        for row in self.rows:
            values.append(row + [""] * max(0, len(self.headers) - len(row)))
        return values

    def insert_row(self, values, index):
        row = list(values) + [""] * max(0, len(self.headers) - len(values))
        self.rows.insert(index - 2, row[: len(self.headers)])

    def add_cols(self, count):
        for _ in range(count):
            self.headers.append("")
            for row in self.rows:
                row.append("")

    def clear(self):
        self.headers = []
        self.rows = []


class FakeWorkbook:
    def __init__(self, worksheets):
        self._worksheets = {worksheet.title: worksheet for worksheet in worksheets}

    def worksheet(self, title):
        worksheet = self._worksheets.get(title)
        if worksheet is None:
            raise WorksheetNotFound(title)
        return worksheet


class ScheduleTests(unittest.TestCase):
    def make_ws(self, rows, headers=None, title=None, spreadsheet=None):
        headers = headers or [
            schedule.COLUMN_SUBJECT,
            schedule.COLUMN_DATE,
            schedule.COLUMN_DONE,
            schedule.COLUMN_LESSON,
            schedule.COLUMN_TITLE,
            schedule.COLUMN_UNIT,
            schedule.COLUMN_NOTE,
            schedule.COLUMN_EXTENSION_COUNT,
        ]
        return FakeWorksheet(headers, rows, title=title, spreadsheet=spreadsheet)

    def make_progress_and_bridge(self, progress_rows, bridge_rows, *, progress_headers=None):
        spreadsheet = FakeSpreadsheet()
        progress_ws = self.make_ws(
            progress_rows,
            headers=progress_headers,
            title=schedule.SHEET_NAME,
            spreadsheet=spreadsheet,
        )
        bridge_ws = FakeWorksheet(
            list(bridge_sheet.BRIDGE_HEADERS),
            bridge_rows,
            title=bridge_sheet.BRIDGE_SHEET_NAME,
            spreadsheet=spreadsheet,
        )
        return progress_ws, bridge_ws

    def test_load_all_rejects_missing_required_headers(self):
        ws = self.make_ws([], headers=[schedule.COLUMN_SUBJECT, schedule.COLUMN_LESSON, schedule.COLUMN_TITLE])
        with self.assertRaises(schedule.SheetFormatError):
            schedule.load_all(ws)

    def test_load_all_keeps_existing_lesson_id(self):
        ws = self.make_ws(
            [["lesson-0007", "Math", "2026-03-24", "FALSE", "1", "Fractions", "Unit 1"]],
            headers=[
                schedule.COLUMN_LESSON_ID,
                schedule.COLUMN_SUBJECT,
                schedule.COLUMN_DATE,
                schedule.COLUMN_DONE,
                schedule.COLUMN_LESSON,
                schedule.COLUMN_TITLE,
                schedule.COLUMN_UNIT,
            ],
        )

        records = schedule.load_all(ws)

        self.assertEqual(records[0][schedule.COLUMN_LESSON_ID], "lesson-0007")
        self.assertEqual(records[0]["_record_key"], "lesson-0007")

    def test_load_all_recovers_bridge_headers_overwritten_on_progress_sheet(self):
        ws = FakeWorksheet(
            [
                "slot_date",
                "slot_period",
                "slot_order",
                schedule.COLUMN_SUBJECT,
                schedule.COLUMN_LESSON_ID,
                "status",
                "source",
                "memo",
                schedule.COLUMN_END_PAGE,
                schedule.COLUMN_NOTE,
                schedule.COLUMN_LESSON_ID,
                schedule.COLUMN_DATE,
                "planned_period",
            ],
            [
                [
                    "Bridge header recovery",
                    "Korean",
                    "1. Unit",
                    "1",
                    "2026-03-10",
                    "TRUE",
                    r"D:\book.pdf",
                    "",
                    "",
                    "",
                    "lesson-0001",
                    "",
                    "",
                ]
            ],
        )

        records = schedule.load_all(ws)
        header_map = schedule.get_header_map(ws)

        self.assertEqual(records[0][schedule.COLUMN_TITLE], "Bridge header recovery")
        self.assertEqual(records[0][schedule.COLUMN_SUBJECT], "Korean")
        self.assertEqual(records[0][schedule.COLUMN_UNIT], "1. Unit")
        self.assertEqual(records[0][schedule.COLUMN_LESSON], "1")
        self.assertEqual(records[0][schedule.COLUMN_DATE], "2026-03-10")
        self.assertEqual(records[0][schedule.COLUMN_DONE], "TRUE")
        self.assertEqual(records[0][schedule.COLUMN_LESSON_ID], "lesson-0001")
        self.assertEqual(header_map[schedule.COLUMN_SUBJECT], 2)
        self.assertEqual(header_map[schedule.COLUMN_DATE], 5)
        self.assertEqual(header_map[schedule.COLUMN_LESSON_ID], 11)

    def test_load_all_recovers_corrupted_progress_headers_without_sample_row_signal(self):
        ws = FakeWorksheet(
            [
                "slot_date",
                "slot_period",
                "slot_order",
                schedule.COLUMN_SUBJECT,
                schedule.COLUMN_LESSON_ID,
                "status",
                "source",
                "memo",
                schedule.COLUMN_END_PAGE,
                schedule.COLUMN_NOTE,
                schedule.COLUMN_LESSON_ID,
                schedule.COLUMN_DATE,
                "planned_period",
            ],
            [
                ["", "", "", "", "", "", "", "", "", "", "", "", ""],
                [
                    "Recovered title",
                    "Science",
                    "2. Unit",
                    "8(7~8)",
                    "2026-04-03",
                    "FALSE",
                    r"D:\book.pdf",
                    "",
                    "",
                    "",
                    "lesson-0008",
                    "",
                    "",
                ],
            ],
        )

        records = schedule.load_all(ws)

        self.assertEqual(records[1][schedule.COLUMN_SUBJECT], "Science")
        self.assertEqual(records[1][schedule.COLUMN_TITLE], "Recovered title")
        self.assertEqual(records[1][schedule.COLUMN_LESSON], "8(7~8)")

    def test_get_next_class_picks_earliest_scheduled_incomplete_row(self):
        ws = self.make_ws(
            [
                ["Math", "2026-03-28", "FALSE", "3", "Division", "Unit 1"],
                ["Math", "", "FALSE", "1", "Intro", "Unit 1"],
                ["Math", "2026-03-24", "TRUE", "1", "Review", "Unit 1"],
                ["Math", "2026-03-25", "FALSE", "2", "Fractions", "Unit 1"],
            ]
        )
        records = schedule.load_all(ws)

        next_class = schedule.get_next_class(records, "Math")

        self.assertEqual(next_class[schedule.COLUMN_LESSON], "2")
        self.assertEqual(next_class[schedule.COLUMN_DATE], "2026-03-25")

    def test_mark_done_uses_actual_done_column_position(self):
        ws = self.make_ws(
            [["Fractions", "FALSE", "Math", "1", "2026-03-24"]],
            headers=[
                schedule.COLUMN_TITLE,
                schedule.COLUMN_DONE,
                schedule.COLUMN_SUBJECT,
                schedule.COLUMN_LESSON,
                schedule.COLUMN_DATE,
            ],
        )
        records = schedule.load_all(ws)

        result = schedule.mark_done(ws, records, "Math", date(2026, 3, 24))

        self.assertEqual(result["updated"], 1)
        update = ws.spreadsheet.batch_updates[0]["data"][0]
        self.assertEqual(update["range"], f"{ws.title}!B2")
        self.assertEqual(update["values"], [[True]])

    def test_push_schedule_filters_by_from_date_and_skips_done_rows(self):
        ws = self.make_ws(
            [
                ["Math", "2026-03-24", "FALSE", "1", "Review", "Unit 1", "[연장일정:2026-03-25]", "1"],
                ["Math", "2026-03-25", "TRUE", "2", "Fractions", "Unit 1", "", ""],
                ["Math", "2026-03-26", "FALSE", "3", "Division", "Unit 1", "", ""],
            ]
        )
        records = schedule.load_all(ws)

        result = schedule.push_schedule(ws, records, "Math", 7, date(2026, 3, 25))

        self.assertEqual(result["updated"], 1)
        self.assertEqual(ws.rows[0][6], "[연장일정:2026-03-25]")
        self.assertEqual(ws.rows[2][1], "2026-04-02")

    def test_extend_lesson_inserts_copy_below_next_class(self):
        ws = self.make_ws(
            [
                ["Math", "2026-03-24", "TRUE", "1", "Review", "Unit 1"],
                ["Math", "2026-03-25", "FALSE", "2", "Fractions", "Unit 1"],
                ["Math", "2026-03-26", "FALSE", "3", "Division", "Unit 1"],
            ]
        )
        records = schedule.load_all(ws)

        result = schedule.extend_lesson(ws, records, "Math")

        self.assertEqual(result["updated"], 2)
        self.assertEqual(ws.rows[1][6], "[연장일정:2026-03-26]")
        self.assertEqual(ws.rows[2][1], "2026-03-27")

    def test_get_schedule_by_date_uses_bridge_rows_when_present(self):
        progress_ws, _bridge_ws = self.make_progress_and_bridge(
            [
                ["lesson-0001", "Math", "2026-03-10", "FALSE", "1", "Fractions", "Unit 1"],
            ],
            [
                ["2026-03-12", 2, 1, "Math", "lesson-0001", "planned", "progress_sync", ""],
            ],
            progress_headers=[
                schedule.COLUMN_LESSON_ID,
                schedule.COLUMN_SUBJECT,
                schedule.COLUMN_DATE,
                schedule.COLUMN_DONE,
                schedule.COLUMN_LESSON,
                schedule.COLUMN_TITLE,
                schedule.COLUMN_UNIT,
            ],
        )
        records = schedule.load_all(progress_ws)
        bridge_rows = schedule.load_bridge_rows_for_progress_ws(progress_ws)

        lessons = schedule.get_schedule_by_date(records, date(2026, 3, 12), bridge_rows=bridge_rows)

        self.assertEqual(len(lessons), 1)
        self.assertEqual(lessons[0][schedule.COLUMN_DATE], "2026-03-12")
        self.assertEqual(lessons[0]["_bridge_row"], 2)

    def test_mark_done_via_bridge_marks_one_slot_at_a_time(self):
        progress_ws, bridge_ws = self.make_progress_and_bridge(
            [
                ["lesson-0001", "Math", "2026-03-03", "FALSE", "1", "Fractions", "Unit 1"],
            ],
            [
                ["2026-03-03", 1, 1, "Math", "lesson-0001", "planned", "progress_sync", ""],
                ["2026-03-10", 1, 2, "Math", "lesson-0001", "planned", "manual_extend", ""],
            ],
            progress_headers=[
                schedule.COLUMN_LESSON_ID,
                schedule.COLUMN_SUBJECT,
                schedule.COLUMN_DATE,
                schedule.COLUMN_DONE,
                schedule.COLUMN_LESSON,
                schedule.COLUMN_TITLE,
                schedule.COLUMN_UNIT,
            ],
        )

        records = schedule.load_all(progress_ws)
        first = schedule.mark_done(progress_ws, records, "Math", bridge_row_number=2)
        first_records = schedule.load_all(progress_ws)

        self.assertEqual(first["updated"], 1)
        self.assertEqual(bridge_ws.rows[0][5], "done")
        self.assertEqual(bridge_ws.rows[1][5], "planned")
        self.assertFalse(schedule._is_done(first_records[0]))

        second_records = schedule.load_all(progress_ws)
        second = schedule.mark_done(progress_ws, second_records, "Math", bridge_row_number=3)
        finished_records = schedule.load_all(progress_ws)

        self.assertEqual(second["updated"], 1)
        self.assertEqual(bridge_ws.rows[0][5], "done")
        self.assertEqual(bridge_ws.rows[1][5], "done")
        self.assertTrue(schedule._is_done(finished_records[0]))

    def test_push_schedule_via_bridge_updates_bridge_and_progress_dates(self):
        progress_ws, bridge_ws = self.make_progress_and_bridge(
            [
                ["lesson-0001", "Math", "2026-03-24", "FALSE", "1", "Fractions", "Unit 1"],
            ],
            [
                ["2026-03-24", 2, 1, "Math", "lesson-0001", "planned", "progress_sync", ""],
            ],
            progress_headers=[
                schedule.COLUMN_LESSON_ID,
                schedule.COLUMN_SUBJECT,
                schedule.COLUMN_DATE,
                schedule.COLUMN_DONE,
                schedule.COLUMN_LESSON,
                schedule.COLUMN_TITLE,
                schedule.COLUMN_UNIT,
            ],
        )
        records = schedule.load_all(progress_ws)

        result = schedule.push_schedule(progress_ws, records, "Math", 7)

        self.assertEqual(result["updated"], 1)
        self.assertEqual(bridge_ws.rows[0][0], "2026-03-31")
        self.assertEqual(progress_ws.rows[0][2], "2026-03-31")

    def test_resolve_progress_worksheet_skips_invalid_first_candidate(self):
        invalid = FakeWorksheet([schedule.COLUMN_SUBJECT, schedule.COLUMN_DONE], [], title="invalid")
        valid = FakeWorksheet(
            [schedule.COLUMN_SUBJECT, schedule.COLUMN_DATE, schedule.COLUMN_DONE, schedule.COLUMN_LESSON],
            [],
            title=schedule.SHEET_NAME,
        )
        workbook = FakeWorkbook([invalid, valid])

        worksheet = schedule.resolve_progress_worksheet(workbook)

        self.assertEqual(worksheet.title, schedule.SHEET_NAME)


if __name__ == "__main__":
    unittest.main()
