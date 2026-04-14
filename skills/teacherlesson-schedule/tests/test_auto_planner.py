import unittest
from datetime import date

import auto_planner


class WorksheetNotFound(Exception):
    pass


class FakeWorksheet:
    def __init__(self, title, headers):
        self.title = title
        self._headers = list(headers)

    def row_values(self, index):
        if index == 1:
            return self._headers[:]
        return []


class FakeWorkbook:
    def __init__(self, worksheets):
        self.worksheets = {worksheet.title: worksheet for worksheet in worksheets}

    def worksheet(self, title):
        worksheet = self.worksheets.get(title)
        if worksheet is None:
            raise WorksheetNotFound(title)
        return worksheet


class AutoPlannerTests(unittest.TestCase):
    def test_is_done_accepts_apostrophe_prefixed_checkbox_values(self):
        self.assertTrue(auto_planner._is_done("'TRUE"))
        self.assertFalse(auto_planner._is_done("'FALSE"))

    def test_build_subject_queues_sorts_by_unit_then_lesson(self):
        records = [
            {"과목": "수학", "대단원": "2. 도형", "차시": "3", "실행여부": ""},
            {"과목": "수학", "대단원": "1. 수와 연산", "차시": "4", "실행여부": ""},
            {"과목": "수학", "대단원": "1. 수와 연산", "차시": "2", "실행여부": ""},
            {"과목": "수학", "대단원": "1. 수와 연산", "차시": "1", "실행여부": "TRUE"},
        ]

        queues = auto_planner.build_subject_queues(records, planner_mode="fill-blanks")

        self.assertEqual(
            [(item["대단원"], item["차시"]) for item in queues["수학"]],
            [("1. 수와 연산", "2"), ("1. 수와 연산", "4"), ("2. 도형", "3")],
        )

    def test_build_subject_queues_excludes_units_not_starting_with_number(self):
        records = [
            {"과목": "국어", "대단원": "1. 생생하게 표현해요", "차시": "10(6~10)", "실행여부": ""},
            {"과목": "국어", "대단원": "① 생생한 느낌을 주는 시", "차시": "11(11~12)", "실행여부": ""},
            {"과목": "국어", "대단원": "학생들끼리 충분히 소통한", "차시": "13", "실행여부": ""},
            {"과목": "국어", "대단원": "2. 분명하고 유창하게", "차시": "1", "실행여부": ""},
        ]

        queues = auto_planner.build_subject_queues(records)

        self.assertEqual(
            [(item["대단원"], item["차시"]) for item in queues["국어"]],
            [
                ("1. 생생하게 표현해요", "10(6~10)"),
                ("2. 분명하고 유창하게", "1"),
            ],
        )

    def test_build_subject_queues_fill_blanks_only_targets_false_and_blank_date(self):
        records = [
            {"과목": "국어", "대단원": "1", "차시": "1", "실행여부": "", "계획일": ""},
            {"과목": "국어", "대단원": "1", "차시": "2", "실행여부": "FALSE", "계획일": ""},
            {"과목": "국어", "대단원": "1", "차시": "3", "실행여부": "FALSE", "계획일": "2026-03-05"},
            {"과목": "국어", "대단원": "1", "차시": "4", "실행여부": "TRUE", "계획일": ""},
        ]

        queues = auto_planner.build_subject_queues(records, planner_mode="fill-blanks")

        self.assertEqual(
            [(item["차시"], item["_row"]) for item in queues["국어"]],
            [("1", 2), ("2", 3)],
        )

    def test_apply_done_column_fallback_reads_f_column_when_header_is_missing(self):
        headers = ["과목", "계획일", "차시", "수업내용", "대단원", ""]
        rows = [
            headers,
            ["국어", "", "1", "도입", "1. 단원", "'TRUE"],
            ["국어", "", "2", "활동", "1. 단원", "'FALSE"],
        ]
        records = [
            {"과목": "국어", "계획일": "", "차시": "1", "수업내용": "도입", "대단원": "1. 단원"},
            {"과목": "국어", "계획일": "", "차시": "2", "수업내용": "활동", "대단원": "1. 단원"},
        ]

        auto_planner.apply_done_column_fallback(headers, rows, records)

        self.assertEqual(records[0]["실행여부"], "'TRUE")
        self.assertEqual(records[1]["실행여부"], "'FALSE")

    def test_build_subject_queues_initial_mode_ignores_execution_status(self):
        records = [
            {"과목": "국어", "대단원": "1", "차시": "1", "실행여부": "TRUE", "계획일": "2026-03-02"},
            {"과목": "국어", "대단원": "1", "차시": "2", "실행여부": "FALSE", "계획일": ""},
        ]

        queues = auto_planner.build_subject_queues(records, planner_mode="initial")

        self.assertEqual([item["차시"] for item in queues["국어"]], ["1", "2"])

    def test_parse_date_accepts_month_day_without_year(self):
        parsed = auto_planner.parse_date("3.2")

        self.assertEqual(parsed, date(date.today().year, 3, 2))

    def test_resolve_subject_start_dates_uses_sheet_and_default_start(self):
        answers = iter([""])
        resolved = auto_planner.resolve_subject_start_dates(
            ["국어", "수학"],
            {"국어": date(2026, 3, 5)},
            date(2026, 3, 2),
            input_fn=lambda _prompt: next(answers),
        )

        self.assertEqual(resolved["국어"], date(2026, 3, 5))
        self.assertEqual(resolved["수학"], date(2026, 3, 2))

    def test_plan_lesson_assignments_respects_subject_start_dates(self):
        subject_queues = {
            "수학": [
                {"_row": 2, "과목": "수학", "대단원": "1", "차시": "1"},
                {"_row": 3, "과목": "수학", "대단원": "1", "차시": "2"},
            ],
            "사회": [
                {"_row": 4, "과목": "사회", "대단원": "1", "차시": "1"},
                {"_row": 5, "과목": "사회", "대단원": "1", "차시": "2"},
            ],
        }
        school_days = [
            date(2026, 3, 2),  # 월
            date(2026, 3, 3),  # 화
            date(2026, 3, 4),  # 수
            date(2026, 3, 5),  # 목
            date(2026, 3, 6),  # 금
        ]
        timetable = {
            0: ["수학"],
            1: ["수학"],
            2: ["사회"],
            3: ["수학"],
            4: ["사회"],
        }
        subject_start_dates = {
            "수학": date(2026, 3, 4),
            "사회": date(2026, 3, 2),
        }

        assignments, remaining = auto_planner.plan_lesson_assignments(
            subject_queues,
            school_days,
            timetable,
            ["수학", "사회"],
            subject_start_dates,
        )

        self.assertEqual(
            [(item["subject"], item["record"]["차시"], item["date"]) for item in assignments],
            [
                ("사회", "1", date(2026, 3, 4)),
                ("수학", "1", date(2026, 3, 5)),
                ("사회", "2", date(2026, 3, 6)),
            ],
        )
        self.assertEqual(len(remaining["수학"]), 1)
        self.assertEqual(remaining["수학"][0]["차시"], "2")

    def test_resolve_progress_worksheet_skips_invalid_first_candidate(self):
        workbook = FakeWorkbook(
            [
                FakeWorksheet("진도표", ["과목", "실행여부"]),
                FakeWorksheet("시트1", ["과목", "계획일", "차시"]),
            ]
        )

        worksheet = auto_planner.resolve_progress_worksheet(workbook)

        self.assertEqual(worksheet.title, "시트1")


if __name__ == "__main__":
    unittest.main()
