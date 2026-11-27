"""깨진 한글 복구(ISSUE-6, T92) 시험.

`auto_planner.py`·`schedule.py`·`server.py` 에 UTF-8 한글이 다른 인코딩으로 잘못 읽힌 채 저장된 글자가 있었다.
문구뿐 아니라 동작에 쓰는 이름(기본 시트 이름, 휴업일 날짜 칸 이름, 진도율 키, 계획교시 키)도 깨져 있었다.
여기서는 ① 동작에 쓰는 이름을 가짜 시트로, ② 깨진 글자가 다시 들어오지 않았는지를 소스 검사로 확인한다.
"""
import contextlib
import importlib
import io
import os
import re
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import auto_planner
import schedule


SKILL_DIR = Path(__file__).resolve().parents[1]
SOURCE_FILES = ["auto_planner.py", "schedule.py", "server.py"]


class WorksheetNotFound(Exception):
    pass


class FakeSheet:
    def __init__(self, title, records=None, headers=None, rows=None):
        self.title = title
        self._records = records or []
        self._headers = list(headers or [])
        self._rows = rows

    def get_all_records(self, **_kwargs):
        return [dict(record) for record in self._records]

    def get_all_values(self):
        return [list(row) for row in (self._rows or [])]

    def row_values(self, index):
        return list(self._headers) if index == 1 else []


class FakeBook:
    def __init__(self, *sheets):
        self.sheets = {sheet.title: sheet for sheet in sheets}

    def worksheet(self, title):
        sheet = self.sheets.get(title)
        if sheet is None:
            raise WorksheetNotFound(title)
        return sheet


class DefaultSheetNameTests(unittest.TestCase):
    def _reload_without_sheet_env(self):
        env = {k: v for k, v in os.environ.items() if k not in {"SHEET_NAME", "SHEET_PROGRESS"}}
        with patch.dict(os.environ, env, clear=True), patch("skill_env.load_env", lambda *a, **k: None):
            return importlib.reload(auto_planner)

    def tearDown(self):
        importlib.reload(auto_planner)

    def test_default_progress_sheet_name_is_sheet1(self):
        module = self._reload_without_sheet_env()
        self.assertEqual(module.LEGACY_PROGRESS_SHEET_NAME, "시트1")
        self.assertEqual(module.PROGRESS_SHEET_NAME, "시트1")

    def test_resolve_progress_worksheet_finds_default_sheet1_without_env(self):
        module = self._reload_without_sheet_env()
        sheet = FakeSheet("시트1", headers=[module.schedule.COLUMN_SUBJECT, module.schedule.COLUMN_DATE])
        self.assertIs(module.resolve_progress_worksheet(FakeBook(sheet)), sheet)

    def test_resolve_progress_worksheet_error_names_the_checked_sheet(self):
        module = self._reload_without_sheet_env()
        with self.assertRaises(ValueError) as ctx:
            module.resolve_progress_worksheet(FakeBook())
        self.assertIn("시트1", str(ctx.exception))


class HolidayColumnTests(unittest.TestCase):
    def test_date_column_found_by_name_even_when_it_is_the_second_column(self):
        book = FakeBook(
            FakeSheet(
                auto_planner.HOLIDAY_SHEET_NAME,
                records=[
                    {"사유": "개교기념일", "날짜": "2026-05-04"},
                    {"사유": "재량휴업일", "날짜": "2026-06-01"},
                ],
            )
        )
        self.assertEqual(
            auto_planner.fetch_holidays(book),
            {date(2026, 5, 4), date(2026, 6, 1)},
        )

    def test_date_column_found_by_name_when_it_is_the_first_column(self):
        book = FakeBook(
            FakeSheet(auto_planner.HOLIDAY_SHEET_NAME, records=[{"날짜": "2026-05-04", "사유": "휴업"}])
        )
        self.assertEqual(auto_planner.fetch_holidays(book), {date(2026, 5, 4)})

    def test_first_column_is_read_when_there_is_no_date_header(self):
        book = FakeBook(
            FakeSheet(auto_planner.HOLIDAY_SHEET_NAME, records=[{"일자": "2026-05-04", "사유": "휴업"}])
        )
        self.assertEqual(auto_planner.fetch_holidays(book), {date(2026, 5, 4)})

    def test_blank_and_unreadable_dates_are_skipped(self):
        book = FakeBook(
            FakeSheet(
                auto_planner.HOLIDAY_SHEET_NAME,
                records=[{"날짜": ""}, {"날짜": "아님"}, {"날짜": "2026-05-04"}],
            )
        )
        self.assertEqual(auto_planner.fetch_holidays(book), {date(2026, 5, 4)})

    def test_missing_holiday_sheet_means_no_holidays_with_korean_notice(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            holidays = auto_planner.fetch_holidays(FakeBook())
        self.assertEqual(holidays, set())
        self.assertIn("휴업일", out.getvalue())
        self.assertIn("시트", out.getvalue())


class TimetableTests(unittest.TestCase):
    def test_weekday_headers_with_yoil_suffix_are_read(self):
        book = FakeBook(
            FakeSheet(
                auto_planner.TIMETABLE_SHEET_NAME,
                rows=[
                    ["교시", "월요일", "화요일", "수요일", "목요일", "금요일"],
                    ["1", "국어", "수학", "사회", "과학", "음악"],
                    ["2", "수학", "", "국어", "체육", ""],
                ],
            )
        )
        with contextlib.redirect_stdout(io.StringIO()):
            timetable = auto_planner.fetch_timetable(book)
        self.assertEqual(timetable[0], ["국어", "수학"])
        self.assertEqual(timetable[1], ["수학"])
        self.assertEqual(timetable[4], ["음악"])

    def test_timetable_without_weekday_headers_reports_korean_error(self):
        book = FakeBook(
            FakeSheet(auto_planner.TIMETABLE_SHEET_NAME, rows=[["교시", "A", "B"], ["1", "x", "y"]])
        )
        with self.assertRaises(ValueError) as ctx:
            auto_planner.fetch_timetable(book)
        self.assertIn("기초시간표", str(ctx.exception))
        self.assertIn("요일", str(ctx.exception))

    def test_timetable_with_no_data_rows_reports_korean_error(self):
        book = FakeBook(FakeSheet(auto_planner.TIMETABLE_SHEET_NAME, rows=[["교시", "월"]]))
        with self.assertRaises(ValueError) as ctx:
            auto_planner.fetch_timetable(book)
        self.assertIn("기초시간표", str(ctx.exception))


class ProgressPrintTests(unittest.TestCase):
    def test_print_progress_shows_real_counts_and_percentage(self):
        records = [
            {schedule.COLUMN_SUBJECT: "국어", schedule.COLUMN_DONE: "TRUE"},
            {schedule.COLUMN_SUBJECT: "국어", schedule.COLUMN_DONE: "FALSE"},
            {schedule.COLUMN_SUBJECT: "국어", schedule.COLUMN_DONE: "FALSE"},
            {schedule.COLUMN_SUBJECT: "국어", schedule.COLUMN_DONE: "TRUE"},
        ]
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            schedule.print_progress(records, ["국어"])
        text = out.getvalue()
        self.assertIn("50.0%", text)
        self.assertIn("(2/4)", text)
        self.assertIn("#" * 10 + "." * 10, text)


class ServerPeriodFallbackTests(unittest.TestCase):
    def test_serialize_lesson_item_falls_back_to_planned_period_column(self):
        import server

        item = {
            schedule.COLUMN_SUBJECT: "국어",
            schedule.COLUMN_DATE: "2026-05-04",
            "계획교시": "3",
        }
        self.assertEqual(server._serialize_lesson_item(item)["planned_period"], "3")

    def test_slot_period_wins_over_planned_period_column(self):
        import server

        item = {schedule.COLUMN_SUBJECT: "국어", "slot_period": "2", "계획교시": "3"}
        self.assertEqual(server._serialize_lesson_item(item)["planned_period"], "2")


class NoMojibakeInSourceTests(unittest.TestCase):
    """깨진 한글이 소스에 다시 들어오면 알 수 있게 한다."""

    # UTF-8 한글 3바이트 중 앞 2바이트를 잃어 '?' 한 글자가 되고 뒤 1바이트만 남은 모양: '?' 바로 뒤 한글
    LOST_LEAD = re.compile("\\?[\\uac00-\\ud7a3]")
    # 한글을 다른 인코딩으로 잘못 읽으면 나오는 한자(CJK 통합 한자) 와 대체 문자
    HANJA = re.compile("[\\u3400-\\u9fff\\uf900-\\ufaff\\ue000-\\uf8ff\\ufffd]")

    def _lines(self, name):
        text = (SKILL_DIR / name).read_text(encoding="utf-8-sig")
        return list(enumerate(text.splitlines(), 1))

    def test_no_hanja_or_replacement_characters_in_sources(self):
        for name in SOURCE_FILES:
            bad = [f"{name}:{n}" for n, line in self._lines(name) if self.HANJA.search(line)]
            with self.subTest(file=name):
                self.assertEqual(bad[:10], [], f"깨진 한글(한자 섞임) {len(bad)}줄")

    def test_no_question_mark_directly_before_hangul_in_sources(self):
        for name in SOURCE_FILES:
            bad = [f"{name}:{n}" for n, line in self._lines(name) if self.LOST_LEAD.search(line)]
            with self.subTest(file=name):
                self.assertEqual(bad[:10], [], f"깨진 한글('?'+한글) {len(bad)}줄")

    def test_sources_stay_valid_utf8(self):
        for name in SOURCE_FILES:
            with self.subTest(file=name):
                (SKILL_DIR / name).read_bytes().decode("utf-8")


if __name__ == "__main__":
    unittest.main()
