import re
import unittest
from datetime import date

import schedule


class FakeSpreadsheet:
    def __init__(self, worksheet):
        self.worksheet = worksheet
        self.batch_updates = []

    def values_batch_update(self, payload):
        self.batch_updates.append(payload)
        for update in payload.get("data", []):
            match = re.search(r"!([A-Z]+)(\d+)$", update.get("range", ""))
            if not match:
                continue
            col_letters, row_number = match.groups()
            col_index = 0
            for char in col_letters:
                col_index = col_index * 26 + (ord(char) - 64)
            row_index = int(row_number) - 2
            col_index -= 1

            while row_index >= len(self.worksheet.rows):
                self.worksheet.rows.append([""] * len(self.worksheet.headers))

            row = self.worksheet.rows[row_index]
            while len(row) < len(self.worksheet.headers):
                row.append("")

            row[col_index] = update["values"][0][0]


class FakeWorksheet:
    def __init__(self, headers, rows):
        self.headers = list(headers)
        self.rows = [list(row) for row in rows]
        self.spreadsheet = FakeSpreadsheet(self)

    def row_values(self, index):
        if index == 1:
            return self.headers[:]
        row_index = index - 2
        if 0 <= row_index < len(self.rows):
            return self.rows[row_index][:]
        return []

    def get_all_records(self, default_blank=""):
        records = []
        for row in self.rows:
            expanded = row + [default_blank] * (len(self.headers) - len(row))
            records.append(
                {
                    header: expanded[idx]
                    for idx, header in enumerate(self.headers)
                }
            )
        return records

    def get_all_values(self):
        values = [self.headers[:]]
        for row in self.rows:
            expanded = row + [""] * (len(self.headers) - len(row))
            values.append(expanded[: len(self.headers)])
        return values

    def insert_row(self, values, index):
        self.rows.insert(index - 2, list(values))


class ScheduleTests(unittest.TestCase):
    def make_ws(self, rows, headers=None):
        headers = headers or [
            "과목",
            "계획일",
            "실행여부",
            "차시",
            "수업내용",
            "대단원",
            "비고",
            "연장횟수",
        ]
        return FakeWorksheet(headers, rows)

    def test_load_all_rejects_missing_required_headers(self):
        ws = self.make_ws([], headers=["과목", "차시", "수업내용"])

        with self.assertRaises(schedule.SheetFormatError):
            schedule.load_all(ws)

    def test_load_all_rejects_invalid_date_format(self):
        ws = self.make_ws(
            [
                ["수학", "2026.13.01", "FALSE", "1", "분수", "수와 연산"],
            ]
        )

        with self.assertRaises(ValueError):
            schedule.load_all(ws)

    def test_get_next_class_picks_earliest_scheduled_incomplete_row(self):
        ws = self.make_ws(
            [
                ["수학", "2026-03-28", "FALSE", "3", "분수", "수와 연산"],
                ["수학", "", "FALSE", "1", "도입", "수와 연산"],
                ["수학", "2026-03-24", "TRUE", "1", "복습", "수와 연산"],
                ["수학", "2026-03-25", "FALSE", "2", "약수", "수와 연산"],
            ]
        )
        records = schedule.load_all(ws)

        next_class = schedule.get_next_class(records, "수학")

        self.assertIsNotNone(next_class)
        self.assertEqual(next_class["차시"], "2")
        self.assertEqual(next_class["계획일"], "2026-03-25")

    def test_status_value_one_is_treated_as_completed(self):
        ws = self.make_ws(
            [
                ["음악", "2026-03-06", "1", "2(2~3)", "길고 짧은 음", "1. 만나요 음악 시간"],
                ["음악", "2026-03-13", "0", "4", "리코더 세상", "1. 만나요 음악 시간"],
            ]
        )
        records = schedule.load_all(ws)

        next_class = schedule.get_next_class(records, "음악")
        progress = schedule.get_progress(records, "음악")

        self.assertEqual(next_class["차시"], "4")
        self.assertEqual(progress["완료"], 1)
        self.assertEqual(progress["전체"], 2)

    def test_load_all_uses_f_column_when_done_header_is_missing(self):
        ws = self.make_ws(
            [
                ["음악", "2026-03-06", "2(2~3)", "길고 짧은 음", "1. 만나요 음악 시간", "'true"],
                ["음악", "2026-03-13", "4", "리코더 세상", "1. 만나요 음악 시간", "'false"],
            ],
            headers=["과목", "계획일", "차시", "수업내용", "대단원", ""],
        )
        records = schedule.load_all(ws)

        next_class = schedule.get_next_class(records, "음악")
        progress = schedule.get_progress(records, "음악")

        self.assertEqual(next_class["차시"], "4")
        self.assertEqual(progress["완료"], 1)
        self.assertEqual(progress["전체"], 2)

    def test_lesson_sort_uses_leading_number_from_text(self):
        ws = self.make_ws(
            [
                ["음악", "2026-03-20", "0", "10", "열 번째", "단원"],
                ["음악", "2026-03-20", "0", "2(2~3)", "두 번째", "단원"],
            ]
        )
        records = schedule.load_all(ws)

        next_class = schedule.get_next_class(records, "음악")

        self.assertEqual(next_class["차시"], "2(2~3)")

    def test_get_remaining_week_lessons_returns_today_through_friday(self):
        ws = self.make_ws(
            [
                ["수학", "2026-03-24", "FALSE", "1", "화요일 수업", "단원"],
                ["수학", "2026-03-25", "TRUE", "2", "수요일 완료", "단원"],
                ["수학", "2026-03-27", "0", "3", "금요일 수업", "단원"],
                ["수학", "2026-03-30", "0", "4", "다음 주 월요일", "단원"],
            ]
        )
        records = schedule.load_all(ws)

        lessons = schedule.get_remaining_week_lessons(records, date(2026, 3, 24))

        self.assertEqual([lesson["수업내용"] for lesson in lessons], ["화요일 수업", "금요일 수업"])

    def test_mark_done_uses_actual_done_column_position(self):
        ws = self.make_ws(
            [
                ["분수", "FALSE", "수학", "1", "2026-03-24"],
            ],
            headers=["수업내용", "실행여부", "과목", "차시", "계획일"],
        )
        records = schedule.load_all(ws)

        result = schedule.mark_done(ws, records, "수학", date(2026, 3, 24))

        self.assertEqual(result["updated"], 1)
        self.assertEqual(len(ws.spreadsheet.batch_updates), 1)
        self.assertEqual(ws.spreadsheet.batch_updates[0]["valueInputOption"], "USER_ENTERED")
        update = ws.spreadsheet.batch_updates[0]["data"][0]
        self.assertEqual(update["range"], f"{schedule.SHEET_NAME}!B2")
        self.assertEqual(update["values"], [[True]])

    def test_mark_done_uses_f_column_when_done_header_is_missing(self):
        ws = self.make_ws(
            [
                ["수학", "2026-03-24", "1", "분수", "수와 연산", "'false"],
            ],
            headers=["과목", "계획일", "차시", "수업내용", "대단원", ""],
        )
        records = schedule.load_all(ws)

        result = schedule.mark_done(ws, records, "수학", date(2026, 3, 24))

        self.assertEqual(result["updated"], 1)
        update = ws.spreadsheet.batch_updates[0]["data"][0]
        self.assertEqual(update["range"], f"{schedule.SHEET_NAME}!F2")
        self.assertEqual(update["values"], [[True]])

    def test_push_schedule_filters_by_from_date_and_skips_done_rows(self):
        ws = self.make_ws(
            [
                ["수학", "2026-03-24", "FALSE", "1", "복습", "수와 연산", "[연장일정:2026-03-25]", "1"],
                ["수학", "2026-03-25", "TRUE", "2", "분수", "수와 연산"],
                ["수학", "2026-03-26", "FALSE", "3", "약수", "수와 연산"],
            ],
            headers=["과목", "계획일", "실행여부", "차시", "수업내용", "대단원", "비고", "연장횟수"],
        )
        records = schedule.load_all(ws)

        result = schedule.push_schedule(ws, records, "수학", 7, date(2026, 3, 25))

        self.assertEqual(result["updated"], 1)
        update = ws.spreadsheet.batch_updates[0]["data"][0]
        self.assertEqual(update["range"], f"{schedule.SHEET_NAME}!B4")
        self.assertEqual(update["values"], [["2026-04-02"]])
        self.assertEqual(ws.rows[0][6], "[연장일정:2026-03-25]")

    def test_extend_lesson_inserts_copy_below_next_class(self):
        ws = self.make_ws(
            [
                ["수학", "2026-03-24", "TRUE", "1", "복습", "수와 연산"],
                ["수학", "2026-03-25", "FALSE", "2", "분수", "수와 연산"],
                ["수학", "2026-03-26", "FALSE", "3", "약수", "수와 연산"],
            ]
        )
        records = schedule.load_all(ws)

        result = schedule.extend_lesson(ws, records, "수학")

        self.assertEqual(result["updated"], 2)
        self.assertEqual(ws.rows[1], ["수학", "2026-03-25", "FALSE", "2", "분수", "수와 연산", "[연장일정:2026-03-26]", "1"])
        self.assertEqual(ws.rows[2], ["수학", "2026-03-27", "FALSE", "3", "약수", "수와 연산", "", ""])

    def test_extend_lesson_can_copy_selected_pending_row(self):
        ws = self.make_ws(
            [
                ["수학", "2026-03-25", "FALSE", "2", "분수", "수와 연산"],
                ["수학", "2026-03-26", "FALSE", "3", "약수", "수와 연산"],
                ["수학", "2026-03-27", "FALSE", "4", "곱셈", "수와 연산"],
            ]
        )
        records = schedule.load_all(ws)

        result = schedule.extend_lesson(ws, records, "수학", row_number=3)

        self.assertEqual(result["updated"], 2)
        self.assertEqual(ws.rows[1], ["수학", "2026-03-26", "FALSE", "3", "약수", "수와 연산", "[연장일정:2026-03-27]", "1"])
        self.assertEqual(ws.rows[2], ["수학", "2026-03-28", "FALSE", "4", "곱셈", "수와 연산", "", ""])

    def test_plan_lesson_extension_shows_added_extension_dates_and_shifted_dates(self):
        ws = self.make_ws(
            [
                ["음악", "2026-03-25", "FALSE", "2", "노래", "단원"],
                ["음악", "2026-03-27", "FALSE", "3", "리듬", "단원"],
                ["음악", "2026-04-01", "FALSE", "4", "기악", "단원"],
            ]
        )
        records = schedule.load_all(ws)

        plan = schedule.plan_lesson_extension(records, "음악", row_number=3)

        self.assertEqual(plan["target_record"]["차시"], "3")
        self.assertEqual(plan["added_extension_dates"], [date(2026, 4, 1)])
        self.assertEqual(
            [(item["record"]["차시"], item["new_planned_date"]) for item in plan["record_updates"]],
            [("4", date(2026, 4, 6))],
        )

    def test_get_schedule_by_date_includes_extension_dates_from_note(self):
        ws = self.make_ws(
            [
                ["음악", "2026-03-25", "FALSE", "2", "노래", "단원", "[연장일정:2026-03-27]", "1"],
            ]
        )
        records = schedule.load_all(ws)

        lessons = schedule.get_schedule_by_date(records, date(2026, 3, 27))

        self.assertEqual(len(lessons), 1)
        self.assertEqual(lessons[0]["수업내용"], "노래")

    def test_parse_date_handles_korean_spaced_dot_format(self):
        """'2026. 3. 2' 형식 (공백+점) 날짜가 올바르게 파싱되는지 확인"""
        result = schedule._parse_date("2026. 3. 2")
        self.assertEqual(result, date(2026, 3, 2))

    def test_parse_date_handles_korean_format_with_padding(self):
        result = schedule._parse_date("2026. 5. 25")
        self.assertEqual(result, date(2026, 5, 25))

    def test_parse_date_standard_formats_still_work(self):
        self.assertEqual(schedule._parse_date("2026-03-02"), date(2026, 3, 2))
        self.assertEqual(schedule._parse_date("2026/03/02"), date(2026, 3, 2))
        self.assertEqual(schedule._parse_date("2026.03.02"), date(2026, 3, 2))

    def test_parse_date_blank_returns_none(self):
        self.assertIsNone(schedule._parse_date(""))
        self.assertIsNone(schedule._parse_date(None))


if __name__ == "__main__":
    unittest.main()
