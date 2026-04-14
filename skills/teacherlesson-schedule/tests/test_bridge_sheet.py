import unittest

import bridge_sheet


class BridgeSheetTests(unittest.TestCase):
    def make_record(
        self,
        *,
        lesson_id,
        subject,
        planned_date="2026-03-02",
        planned_period="",
        lesson="1",
        row=2,
        done=False,
    ):
        return {
            "lesson_id": lesson_id,
            "과목": subject,
            "계획일": planned_date,
            "계획교시": planned_period,
            "차시": lesson,
            "실행여부": "TRUE" if done else "FALSE",
            "_row": row,
        }

    def test_build_bridge_rows_preserves_explicit_period(self):
        records = [
            self.make_record(
                lesson_id="lesson-0001",
                subject="국어",
                planned_period="3교시",
            )
        ]
        timetable = {0: ["국어", "수학", "국어"]}

        rows = bridge_sheet.build_bridge_rows_from_progress(records, timetable)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["slot_period"], 3)
        self.assertEqual(rows[0]["slot_order"], 1)
        self.assertEqual(rows[0]["memo"], "")

    def test_build_bridge_rows_inferrs_periods_from_timetable(self):
        records = [
            self.make_record(lesson_id="lesson-0001", subject="국어", lesson="1", row=2),
            self.make_record(lesson_id="lesson-0002", subject="국어", lesson="2", row=3),
        ]
        timetable = {0: ["국어", "수학", "국어"]}

        rows = bridge_sheet.build_bridge_rows_from_progress(records, timetable)

        self.assertEqual(
            [(row["lesson_id"], row["slot_period"], row["slot_order"]) for row in rows],
            [
                ("lesson-0001", 1, 1),
                ("lesson-0002", 3, 2),
            ],
        )

    def test_build_bridge_rows_marks_period_unmatched_when_slots_run_out(self):
        records = [
            self.make_record(lesson_id="lesson-0001", subject="수학", lesson="1", row=2),
            self.make_record(lesson_id="lesson-0002", subject="수학", lesson="2", row=3),
        ]
        timetable = {0: ["수학"]}

        rows = bridge_sheet.build_bridge_rows_from_progress(records, timetable)

        self.assertEqual(rows[0]["slot_period"], 1)
        self.assertEqual(rows[1]["slot_period"], "")
        self.assertEqual(rows[1]["memo"], bridge_sheet.PERIOD_UNMATCHED_MEMO)

    def test_build_bridge_rows_marks_done_status(self):
        records = [
            self.make_record(
                lesson_id="lesson-0001",
                subject="음악",
                done=True,
            )
        ]
        timetable = {0: ["음악"]}

        rows = bridge_sheet.build_bridge_rows_from_progress(records, timetable)

        self.assertEqual(rows[0]["status"], bridge_sheet.STATUS_DONE)

    def test_build_progress_sync_rows_chooses_earliest_slot(self):
        records = [
            self.make_record(lesson_id="lesson-0001", subject="국어", row=2),
            self.make_record(lesson_id="lesson-0002", subject="수학", row=3, planned_date=""),
        ]
        bridge_rows = [
            {
                "slot_date": "2026-03-03",
                "slot_period": 2,
                "slot_order": 1,
                "과목": "국어",
                "lesson_id": "lesson-0001",
                "status": "planned",
                "source": "progress_sync",
                "memo": "",
            },
            {
                "slot_date": "2026-03-02",
                "slot_period": 3,
                "slot_order": 1,
                "과목": "국어",
                "lesson_id": "lesson-0001",
                "status": "planned",
                "source": "progress_sync",
                "memo": "",
            },
        ]

        sync_rows = bridge_sheet.build_progress_sync_rows(records, bridge_rows)

        self.assertEqual(
            sync_rows,
            [
                {
                    "row": 2,
                    "lesson_id": "lesson-0001",
                    "계획일": "2026-03-02",
                    "계획교시": 3,
                },
                {
                    "row": 3,
                    "lesson_id": "lesson-0002",
                    "계획일": "",
                    "계획교시": "",
                },
            ],
        )

    def test_plan_bridge_rows_assigns_periods_from_timetable_sequence(self):
        subject_queues = {
            "과학": [
                self.make_record(lesson_id="lesson-0001", subject="과학", lesson="1", row=2),
                self.make_record(lesson_id="lesson-0002", subject="과학", lesson="2", row=3),
            ],
            "국어": [
                self.make_record(lesson_id="lesson-0003", subject="국어", lesson="1", row=4),
            ],
        }
        school_days = [bridge_sheet.schedule.date(2026, 3, 3)]
        timetable = {
            1: ["과학", "과학", "국어", "수학"],
        }
        subject_start_dates = {
            "과학": bridge_sheet.schedule.date(2026, 3, 2),
            "국어": bridge_sheet.schedule.date(2026, 3, 2),
        }

        rows, remaining = bridge_sheet.plan_bridge_rows(
            subject_queues,
            school_days,
            timetable,
            subject_start_dates,
        )

        self.assertEqual(
            [(row["lesson_id"], row["slot_period"], row["slot_order"]) for row in rows],
            [
                ("lesson-0001", 1, 1),
                ("lesson-0002", 2, 2),
                ("lesson-0003", 3, 1),
            ],
        )
        self.assertEqual(len(remaining["과학"]), 0)
        self.assertEqual(len(remaining["국어"]), 0)

    def test_plan_bridge_rows_respects_subject_start_dates(self):
        subject_queues = {
            "수학": [
                self.make_record(lesson_id="lesson-0001", subject="수학", lesson="1", row=2),
            ],
        }
        school_days = [
            bridge_sheet.schedule.date(2026, 3, 2),
            bridge_sheet.schedule.date(2026, 3, 3),
        ]
        timetable = {
            0: ["수학"],
            1: ["수학"],
        }
        subject_start_dates = {
            "수학": bridge_sheet.schedule.date(2026, 3, 3),
        }

        rows, _remaining = bridge_sheet.plan_bridge_rows(
            subject_queues,
            school_days,
            timetable,
            subject_start_dates,
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["slot_date"], "2026-03-03")
        self.assertEqual(rows[0]["slot_period"], 1)

    def test_build_bridge_subject_queues_keeps_non_numeric_unit_rows(self):
        records = [
            {
                "lesson_id": "lesson-0001",
                "과목": "국어",
                "대단원": "독서 단원",
                "차시": "2",
                "실행여부": "FALSE",
                "_row": 3,
            },
            {
                "lesson_id": "lesson-0002",
                "과목": "국어",
                "대단원": "말하기 단원",
                "차시": "1",
                "실행여부": "FALSE",
                "_row": 2,
            },
        ]

        queues = bridge_sheet.build_bridge_subject_queues(records, planner_mode="initial")

        self.assertEqual(
            [item["lesson_id"] for item in queues["국어"]],
            ["lesson-0002", "lesson-0001"],
        )

    def test_plan_bridge_rows_matches_subject_despite_spacing_difference(self):
        subject_queues = {
            "援?뼱": [
                self.make_record(lesson_id="lesson-0001", subject="援?뼱", lesson="1", row=2),
            ],
        }
        school_days = [bridge_sheet.schedule.date(2026, 3, 2)]
        timetable = {
            0: ["援 ?뼱"],
        }
        subject_start_dates = {
            "援?뼱": bridge_sheet.schedule.date(2026, 3, 2),
        }

        rows, _remaining = bridge_sheet.plan_bridge_rows(
            subject_queues,
            school_days,
            timetable,
            subject_start_dates,
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["lesson_id"], "lesson-0001")
        self.assertEqual(rows[0]["slot_period"], 1)


if __name__ == "__main__":
    unittest.main()
