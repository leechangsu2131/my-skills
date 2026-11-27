"""server.py 쓰기 경로 6개가 시트 오류(ScheduleError)를 JSON 오류로 바꾸는지 시험 (S3, ISSUE-005).

`/api/done`·`push`·`extend`·`pull`·`move`·`swap` 은 `except ValueError` 만 있어서,
시트 읽기·머리글 문제(ScheduleError)가 나면 JSON 이 아닌 서버 오류로 올라온다.
`/api/catch-up`·`/api/lessons` 는 이미 고쳐졌다(ISSUE-001·002).

지금 동작은 xfail 로 표시해 둔다. 고치면(`except schedule.ScheduleError` 추가) 시험이 통과하면서
xfail(strict) 때문에 실패로 바뀌니, 그때 `@unittest.expectedFailure` 를 지운다.
소스(server.py)는 고치지 않는다. 시트·네트워크·비밀값 없이 가짜로 돈다.
"""

import unittest
from unittest.mock import patch

import schedule
import server

# (주소, 보낼 내용) — 시트를 읽기 전에 막히지 않도록 필요한 값은 채워 둔다.
WRITE_PATHS = (
    ("/api/done", {"subject": "수학"}),
    ("/api/push", {"subject": "수학", "days": 7}),
    ("/api/extend", {"subject": "수학"}),
    ("/api/pull", {"bridge_row": 2, "subject": "수학"}),
    ("/api/move", {"bridge_row": 2, "direction": "up", "subject": "수학"}),
    ("/api/swap", {"first_bridge_row": 2, "second_bridge_row": 3, "subject": "수학"}),
)


class WriteEndpointsScheduleErrorTests(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()

    def post(self, path, body):
        return self.client.post(path, json=body)

    @unittest.expectedFailure  # ISSUE-005: 아직 안 고침
    def test_connect_failure_is_reported_as_json_error(self):
        """시트 연결 단계에서 ScheduleError 가 나도 JSON 오류(500)로 돌려줘야 한다."""
        for path, body in WRITE_PATHS:
            with self.subTest(path=path), patch.object(
                server.schedule, "connect", side_effect=schedule.SheetFormatError("머리글 이상")
            ):
                try:
                    response = self.post(path, body)
                except schedule.ScheduleError:
                    self.fail(f"{path}: ScheduleError 가 JSON 오류로 바뀌지 않고 그대로 올라옴")
                self.assertEqual(response.status_code, 500)
                data = response.get_json(silent=True)
                self.assertIsNotNone(data, f"{path}: JSON 이 아닌 오류 화면이 돌아옴")
                self.assertEqual(data["status"], "error")
                self.assertIn("머리글 이상", data["message"])

    @unittest.expectedFailure  # ISSUE-005: 아직 안 고침
    def test_read_failure_is_reported_as_json_error(self):
        """시트를 읽는 단계(load_all)에서 ScheduleError 가 나도 마찬가지."""
        for path, body in WRITE_PATHS:
            with self.subTest(path=path), patch.object(
                server.schedule, "connect", return_value=object()
            ), patch.object(
                server.schedule, "load_all", side_effect=schedule.ConfigurationError("설정 없음")
            ):
                try:
                    response = self.post(path, body)
                except schedule.ScheduleError:
                    self.fail(f"{path}: ScheduleError 가 JSON 오류로 바뀌지 않고 그대로 올라옴")
                self.assertEqual(response.status_code, 500)
                data = response.get_json(silent=True)
                self.assertIsNotNone(data, f"{path}: JSON 이 아닌 오류 화면이 돌아옴")
                self.assertEqual(data["status"], "error")

    def test_value_error_still_returns_400_json(self):
        """이미 되는 것: 입력 문제(ValueError)는 400 JSON. 고칠 때 이것이 깨지지 않게 지키는 시험."""
        for path, body in WRITE_PATHS:
            with self.subTest(path=path), patch.object(
                server.schedule, "connect", side_effect=ValueError("입력 이상")
            ):
                response = self.post(path, body)
                self.assertEqual(response.status_code, 400)
                data = response.get_json()
                self.assertEqual(data["status"], "error")
                self.assertIn("입력 이상", data["message"])


if __name__ == "__main__":
    unittest.main()
