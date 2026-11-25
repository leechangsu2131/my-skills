"""server.py 의 `/api/lessons`, `/api/catch-up` 시험 (T04).

Flask test client 로 부르고, 시트 연결·읽기·수업배치(bridge)는 모두 가짜로 바꾼다.
네트워크·비밀값·실제 시트 없이 돈다. 소스(server.py)는 고치지 않는다.
"""

import unittest
from unittest.mock import patch

import schedule
import server


def record(row, subject, lesson, title="", unit="", lesson_id="", done=False, **extra):
    """진도표 한 줄 모양의 가짜 기록."""
    item = {
        "_row": row,
        schedule.COLUMN_SUBJECT: subject,
        schedule.COLUMN_LESSON: str(lesson),
        schedule.COLUMN_TITLE: title,
        schedule.COLUMN_UNIT: unit,
        schedule.COLUMN_LESSON_ID: lesson_id,
        schedule.COLUMN_DONE: "TRUE" if done else "FALSE",
    }
    item.update(extra)
    return item


def bridge_row(lesson_id, slot_date, slot_period, status="planned", subject="수학", order=""):
    """수업배치(bridge) 한 줄 모양의 가짜 기록."""
    return {
        schedule.COLUMN_LESSON_ID: lesson_id,
        schedule.COLUMN_SUBJECT: subject,
        "slot_date": slot_date,
        "slot_period": slot_period,
        "slot_order": order,
        "status": status,
    }


class LessonsEndpointTests(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()

    def get_lessons(self, records, bridge_rows=None, query="?subject=수학"):
        """가짜 시트로 /api/lessons 를 부르고 응답을 돌려준다."""
        bridge = None if bridge_rows is None else {"rows": bridge_rows}
        with (
            patch.object(server.schedule, "connect", return_value=object()),
            patch.object(server.schedule, "load_all", return_value=records),
            patch.object(server.schedule, "_load_bridge_support", return_value=bridge),
        ):
            return self.client.get("/api/lessons" + query)

    # ---- 입력 확인 ----
    def test_missing_subject_returns_400_without_touching_sheet(self):
        with patch.object(server.schedule, "connect") as connect:
            response = self.client.get("/api/lessons")
        self.assertEqual(response.status_code, 400)
        body = response.get_json()
        self.assertEqual(body["status"], "error")
        self.assertIn("subject", body["message"])
        connect.assert_not_called()

    def test_blank_subject_is_treated_as_missing(self):
        with patch.object(server.schedule, "connect") as connect:
            response = self.client.get("/api/lessons?subject=%20%20")
        self.assertEqual(response.status_code, 400)
        connect.assert_not_called()

    # ---- 시트 읽기 실패 ----
    def test_sheet_connect_value_error_returns_500_json(self):
        with patch.object(server.schedule, "connect", side_effect=ValueError("설정 없음")):
            response = self.client.get("/api/lessons?subject=수학")
        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertEqual(body["status"], "error")
        self.assertIn("진도표를 읽지 못했어요", body["message"])
        self.assertIn("설정 없음", body["message"])

    def test_sheet_schedule_error_returns_500_json(self):
        with (
            patch.object(server.schedule, "connect", return_value=object()),
            patch.object(
                server.schedule, "load_all", side_effect=schedule.SheetFormatError("머리글 이상")
            ),
        ):
            response = self.client.get("/api/lessons?subject=수학")
        self.assertEqual(response.status_code, 500)
        self.assertIn("머리글 이상", response.get_json()["message"])

    # ---- 결과 모양 ----
    def test_returns_only_requested_subject_in_sheet_row_order(self):
        records = [
            record(5, "수학", 3, title="셋째", lesson_id="m-3"),
            record(2, "국어", 1, title="국어 첫째", lesson_id="k-1"),
            record(3, "수학", 1, title="첫째", lesson_id="m-1"),
            record(4, "수학", 2, title="둘째", lesson_id="m-2"),
        ]
        response = self.get_lessons(records, bridge_rows=[])
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["status"], "success")
        self.assertEqual(body["subject"], "수학")
        self.assertEqual([item["title"] for item in body["items"]], ["첫째", "둘째", "셋째"])

    def test_subject_must_match_exactly(self):
        records = [record(2, "수학", 1, lesson_id="m-1"), record(3, "수학익힘", 1, lesson_id="mi-1")]
        body = self.get_lessons(records, bridge_rows=[]).get_json()
        self.assertEqual([item["record_key"] for item in body["items"]], ["m-1"])

    def test_unknown_subject_returns_empty_list(self):
        body = self.get_lessons([record(2, "수학", 1, lesson_id="m-1")], bridge_rows=[], query="?subject=과학").get_json()
        self.assertEqual(body["status"], "success")
        self.assertEqual(body["items"], [])

    def test_item_fields_are_cleaned_and_complete(self):
        records = [record(2, "수학", " 4 ", title=" 분수 ", unit=" 3. 분수 ", lesson_id="m-4")]
        item = self.get_lessons(records, bridge_rows=[]).get_json()["items"][0]
        self.assertEqual(
            item,
            {
                "record_key": "m-4",
                "unit": "3. 분수",
                "lesson": "4",
                "title": "분수",
                "done": False,
                "planned_date": "",
                "planned_period": "",
            },
        )

    def test_record_key_falls_back_to_record_key_field_then_row_number(self):
        records = [
            record(2, "수학", 1, lesson_id="", _record_key="rk-7"),
            record(3, "수학", 2, lesson_id=""),
        ]
        items = self.get_lessons(records, bridge_rows=[]).get_json()["items"]
        self.assertEqual([item["record_key"] for item in items], ["rk-7", 3])

    def test_done_flag_follows_progress_sheet(self):
        records = [
            record(2, "수학", 1, lesson_id="m-1", done=True),
            record(3, "수학", 2, lesson_id="m-2", done=False),
        ]
        items = self.get_lessons(records, bridge_rows=[]).get_json()["items"]
        self.assertEqual([item["done"] for item in items], [True, False])

    # ---- 수업배치(bridge)에서 읽는 계획 날짜·교시 ----
    def test_planned_slot_comes_from_bridge(self):
        records = [record(2, "수학", 1, lesson_id="m-1")]
        rows = [bridge_row("m-1", "2026-12-01", "3")]
        item = self.get_lessons(records, rows).get_json()["items"][0]
        self.assertEqual(item["planned_date"], "2026-12-01")
        self.assertEqual(item["planned_period"], "3")

    @unittest.expectedFailure
    def test_bridge_date_with_time_suffix_is_cut_to_ten_chars(self):
        # 기대(추정): 코드가 slot_date 를 [:10] 으로 자르므로 '날짜 시각' 글자도 받아줄 것.
        # 지금은 그 앞의 정렬(_bridge_row_sort_key)이 날짜 형식 오류(ValueError)를 내고
        # try 밖이라 오류가 그대로 올라온다 → teacherlesson-schedule ISSUES 기록 참고.
        records = [record(2, "수학", 1, lesson_id="m-1")]
        rows = [bridge_row("m-1", "2026-12-01 00:00:00", "3")]
        item = self.get_lessons(records, rows).get_json()["items"][0]
        self.assertEqual(item["planned_date"], "2026-12-01")

    def test_earliest_planned_slot_wins_when_lesson_has_several(self):
        records = [record(2, "수학", 1, lesson_id="m-1")]
        rows = [
            bridge_row("m-1", "2026-12-05", "2"),
            bridge_row("m-1", "2026-12-02", "4"),
            bridge_row("m-1", "2026-12-02", "1"),
        ]
        item = self.get_lessons(records, rows).get_json()["items"][0]
        self.assertEqual((item["planned_date"], item["planned_period"]), ("2026-12-02", "1"))

    def test_blank_status_counts_as_planned(self):
        records = [record(2, "수학", 1, lesson_id="m-1")]
        item = self.get_lessons(records, [bridge_row("m-1", "2026-12-01", "2", status="")]).get_json()["items"][0]
        self.assertEqual(item["planned_date"], "2026-12-01")

    def test_non_planned_bridge_rows_are_ignored(self):
        records = [record(2, "수학", 1, lesson_id="m-1")]
        rows = [
            bridge_row("m-1", "2026-11-30", "1", status="done"),
            bridge_row("m-1", "2026-12-03", "5", status="planned"),
        ]
        item = self.get_lessons(records, rows).get_json()["items"][0]
        self.assertEqual((item["planned_date"], item["planned_period"]), ("2026-12-03", "5"))

    def test_lesson_with_only_done_bridge_rows_has_blank_slot(self):
        records = [record(2, "수학", 1, lesson_id="m-1")]
        item = self.get_lessons(records, [bridge_row("m-1", "2026-11-30", "1", status="done")]).get_json()["items"][0]
        self.assertEqual((item["planned_date"], item["planned_period"]), ("", ""))

    def test_done_lesson_never_shows_planned_slot(self):
        records = [record(2, "수학", 1, lesson_id="m-1", done=True)]
        item = self.get_lessons(records, [bridge_row("m-1", "2026-12-01", "2")]).get_json()["items"][0]
        self.assertTrue(item["done"])
        self.assertEqual((item["planned_date"], item["planned_period"]), ("", ""))

    def test_bridge_rows_without_lesson_id_are_ignored(self):
        records = [record(2, "수학", 1, lesson_id="m-1")]
        rows = [bridge_row("", "2026-12-01", "1"), bridge_row("m-1", "2026-12-09", "6")]
        item = self.get_lessons(records, rows).get_json()["items"][0]
        self.assertEqual((item["planned_date"], item["planned_period"]), ("2026-12-09", "6"))

    def test_slot_of_other_lesson_is_not_mixed_in(self):
        records = [
            record(2, "수학", 1, lesson_id="m-1"),
            record(3, "수학", 2, lesson_id="m-2"),
        ]
        rows = [bridge_row("m-2", "2026-12-04", "2")]
        items = self.get_lessons(records, rows).get_json()["items"]
        self.assertEqual(items[0]["planned_date"], "")
        self.assertEqual(items[1]["planned_date"], "2026-12-04")

    def test_works_without_bridge_sheet(self):
        # 수업배치 시트가 없으면(None) 계획 칸은 모두 빈칸이고 오류 없이 목록은 나온다
        records = [record(2, "수학", 1, lesson_id="m-1")]
        response = self.get_lessons(records, bridge_rows=None)
        self.assertEqual(response.status_code, 200)
        item = response.get_json()["items"][0]
        self.assertEqual((item["planned_date"], item["planned_period"]), ("", ""))

    def test_endpoint_does_not_write_or_log(self):
        # 읽기 전용 API: 기록 남기기·캐시 비우기를 하지 않는다
        with (
            patch.object(server, "log_action") as log_action,
            patch.object(server, "_clear_dashboard_cache") as clear_cache,
        ):
            self.get_lessons([record(2, "수학", 1, lesson_id="m-1")], bridge_rows=[])
        log_action.assert_not_called()
        clear_cache.assert_not_called()


class CatchUpEndpointTests(unittest.TestCase):
    def setUp(self):
        server._clear_dashboard_cache()
        self.client = server.app.test_client()

    def tearDown(self):
        server._clear_dashboard_cache()

    def post(self, **kwargs):
        return self.client.post("/api/catch-up", **kwargs)

    def test_success_wraps_result_logs_and_clears_cache(self):
        ws = object()
        result = {"updated": 3, "message": "수학 진도를 맞췄어요"}
        with (
            patch.object(server.schedule, "connect", return_value=ws),
            patch.object(server.schedule, "load_all", return_value=[]),
            patch.object(server.schedule, "catch_up_to_lesson", return_value=result),
            patch.object(server, "log_action") as log_action,
            patch.object(server, "_clear_dashboard_cache") as clear_cache,
        ):
            response = self.post(json={"subject": "수학", "bridge_row": 9, "record_key": "m-5"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(),
            {"status": "success", "message": "수학 진도를 맞췄어요", "result": result},
        )
        log_action.assert_called_once_with("catch_up_to_lesson", "수학", "bridge_row=9, record_key=m-5")
        clear_cache.assert_called_once_with()

    def test_value_error_returns_400_and_skips_log_and_cache_clear(self):
        with (
            patch.object(server.schedule, "connect", return_value=object()),
            patch.object(server.schedule, "load_all", return_value=[]),
            patch.object(
                server.schedule, "catch_up_to_lesson", side_effect=ValueError("해당 차시를 찾지 못했어요")
            ),
            patch.object(server, "log_action") as log_action,
            patch.object(server, "_clear_dashboard_cache") as clear_cache,
        ):
            response = self.post(json={"subject": "수학", "record_key": "없음"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json(), {"status": "error", "message": "해당 차시를 찾지 못했어요"}
        )
        log_action.assert_not_called()
        clear_cache.assert_not_called()

    def test_value_error_from_connect_also_returns_400(self):
        with patch.object(server.schedule, "connect", side_effect=ValueError("연결 설정 오류")):
            response = self.post(json={"subject": "수학"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["message"], "연결 설정 오류")

    def test_missing_optional_fields_are_passed_as_none(self):
        ws = object()
        with (
            patch.object(server.schedule, "connect", return_value=ws),
            patch.object(server.schedule, "load_all", return_value=["r"]),
            patch.object(server.schedule, "catch_up_to_lesson", return_value={"message": ""}) as catch_up,
            patch.object(server, "log_action") as log_action,
        ):
            response = self.post(json={"subject": "수학"})
        self.assertEqual(response.status_code, 200)
        catch_up.assert_called_once_with(ws, ["r"], "수학", bridge_row_number=None, record_key=None)
        log_action.assert_called_once_with("catch_up_to_lesson", "수학", "bridge_row=None, record_key=")

    def test_empty_json_body_passes_blank_subject(self):
        # 본문이 빈 JSON 이어도 서버가 죽지 않고, 과목 없음은 schedule 쪽 판단에 맡긴다
        ws = object()
        with (
            patch.object(server.schedule, "connect", return_value=ws),
            patch.object(server.schedule, "load_all", return_value=[]),
            patch.object(
                server.schedule, "catch_up_to_lesson", side_effect=ValueError("과목이 필요해요")
            ) as catch_up,
            patch.object(server, "log_action"),
        ):
            response = self.post(json={})
        self.assertEqual(response.status_code, 400)
        catch_up.assert_called_once_with(ws, [], "", bridge_row_number=None, record_key=None)

    def test_success_clears_previously_cached_dashboard(self):
        server._store_cached_dashboard_payload(None, {"cached": True})
        self.assertIsNotNone(server._get_cached_dashboard_payload(None))
        with (
            patch.object(server.schedule, "connect", return_value=object()),
            patch.object(server.schedule, "load_all", return_value=[]),
            patch.object(server.schedule, "catch_up_to_lesson", return_value={"message": "ok"}),
            patch.object(server, "log_action"),
        ):
            self.post(json={"subject": "수학"})
        self.assertIsNone(server._get_cached_dashboard_payload(None))

    def test_failed_request_keeps_cached_dashboard(self):
        server._store_cached_dashboard_payload(None, {"cached": True})
        with (
            patch.object(server.schedule, "connect", return_value=object()),
            patch.object(server.schedule, "load_all", return_value=[]),
            patch.object(server.schedule, "catch_up_to_lesson", side_effect=ValueError("실패")),
            patch.object(server, "log_action"),
        ):
            self.post(json={"subject": "수학"})
        self.assertEqual(server._get_cached_dashboard_payload(None), {"cached": True})

    def test_get_method_is_not_allowed(self):
        self.assertEqual(self.client.get("/api/catch-up").status_code, 405)

    @unittest.expectedFailure
    def test_schedule_error_returns_json_error_like_lessons_endpoint(self):
        # 기대(추정): 시트 읽기 실패(ScheduleError)도 /api/lessons 처럼 JSON 오류로 돌려준다.
        # 지금은 ValueError 만 잡아서 ScheduleError 가 그대로 올라온다 → teacherlesson-schedule ISSUES 기록 참고.
        with patch.object(
            server.schedule, "connect", side_effect=schedule.SheetFormatError("머리글 이상")
        ):
            try:
                response = self.post(json={"subject": "수학"})
            except schedule.ScheduleError:
                self.fail("ScheduleError 가 JSON 오류로 바뀌지 않고 그대로 올라옴")
        self.assertIn(response.status_code, (400, 500))
        self.assertEqual(response.get_json()["status"], "error")


if __name__ == "__main__":
    unittest.main()
