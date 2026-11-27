"""쓰기 경로 6개(`/api/done`·`push`·`extend`·`pull`·`move`·`swap`)가 ScheduleError 를 JSON 오류로 바꾸는지 (ISSUE-005, S3).

`/api/catch-up`·`/api/lessons` 는 이미 고쳐졌다(ISSUE-001·002). 이 6개는 `except ValueError` 만 있어
`schedule.ScheduleError`(ValueError 의 하위가 아님)가 나면 JSON 이 아니라 파이썬 오류로 올라온다 — T100 에서 `server._json_schedule_errors`
(ScheduleError → JSON 500)를 6개 경로에 붙여 고쳤다. 처음엔 expectedFailure 였다.

Flask test client + 가짜 시트라 네트워크·비밀값 없이 돈다.
"""
import unittest
from unittest.mock import patch

import schedule
import server

ROUTES = {
    "done": {"subject": "수학"},
    "push": {"subject": "수학", "days": 1},
    "extend": {"subject": "수학"},
    "pull": {"subject": "수학", "bridge_row": 2},
    "move": {"subject": "수학", "bridge_row": 2, "direction": "up"},
    "swap": {"subject": "수학", "first_bridge_row": 2, "second_bridge_row": 3},
}
ERRORS = (schedule.SheetFormatError("머리글 이상"), schedule.ConfigurationError("설정 없음"))


class WriteRoutesScheduleErrorTests(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()

    def post(self, route, **patches):
        with patch.object(server.schedule, "connect", **patches):
            return self.client.post(f"/api/{route}", json=ROUTES[route])

    def check_json_error(self, route):
        for error in ERRORS:
            with self.subTest(route=route, error=type(error).__name__):
                try:
                    response = self.post(route, side_effect=error)
                except schedule.ScheduleError:
                    self.fail("ScheduleError 가 JSON 오류로 바뀌지 않고 그대로 올라옴")
                self.assertEqual(response.status_code, 500)
                body = response.get_json()
                self.assertEqual(body["status"], "error")
                self.assertIn(str(error), body["message"])

    # --- ISSUE-005 (T100 에서 고침) ---
    def test_done_schedule_error_is_json(self):
        self.check_json_error("done")

    def test_push_schedule_error_is_json(self):
        self.check_json_error("push")

    def test_extend_schedule_error_is_json(self):
        self.check_json_error("extend")

    def test_pull_schedule_error_is_json(self):
        self.check_json_error("pull")

    def test_move_schedule_error_is_json(self):
        self.check_json_error("move")

    def test_swap_schedule_error_is_json(self):
        self.check_json_error("swap")

    # --- 이미 되는 것(회귀 방지): ValueError 는 400 JSON ---
    def test_value_error_is_still_400_json_on_every_route(self):
        for route in ROUTES:
            with self.subTest(route=route):
                response = self.post(route, side_effect=ValueError("값 오류"))
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.get_json()["status"], "error")
                self.assertIn("값 오류", response.get_json()["message"])

    def test_catch_up_already_converts_schedule_error(self):
        with patch.object(server.schedule, "connect", side_effect=schedule.SheetFormatError("머리글 이상")):
            response = self.client.post("/api/catch-up", json={"subject": "수학"})
        self.assertEqual(response.status_code, 500)


if __name__ == "__main__":
    unittest.main()
