"""memo_sync.py 의 pull_due(내려받을 때가 됐나)·key_of(메모의 서버 키 고르기) 시험 (S1).

    python -m unittest discover -s tests -v      (skills/teacherlesson-assistant 폴더에서)

네트워크·Supabase 는 부르지 않는다. 상태 파일은 임시 폴더에 만든다.
"""
import json
import pathlib
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import memo_sync as ms  # noqa: E402

NOW = datetime(2026, 11, 27, 12, 0, 0)


class PullDueTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.data = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def write_state(self, last):
        raw = last.isoformat() if isinstance(last, datetime) else last
        (self.data / "memo_sync_state.json").write_text(json.dumps({"last_pull": raw}), encoding="utf-8")

    def due(self, hours, now=NOW):
        return ms.pull_due(hours, self.data, now)

    def test_no_record_means_due(self):
        self.assertTrue(self.due(6))

    def test_recent_pull_is_not_due(self):
        self.write_state(NOW - timedelta(hours=1))
        self.assertFalse(self.due(6))

    def test_old_pull_is_due(self):
        self.write_state(NOW - timedelta(hours=7))
        self.assertTrue(self.due(6))

    def test_exactly_the_limit_is_due_and_just_under_is_not(self):
        self.write_state(NOW - timedelta(hours=6))
        self.assertTrue(self.due(6))
        self.write_state(NOW - timedelta(hours=6) + timedelta(seconds=1))
        self.assertFalse(self.due(6))

    def test_zero_hours_is_always_due(self):
        self.write_state(NOW)
        self.assertTrue(self.due(0))

    def test_fractional_hours(self):
        self.write_state(NOW - timedelta(minutes=20))
        self.assertTrue(self.due(0.25))
        self.assertFalse(self.due(0.5))

    def test_unreadable_state_means_due(self):
        for raw in ("{깨진 글", "[]", '{"last_pull": "어제"}', '{"last_pull": ""}', '{"other": 1}'):
            (self.data / "memo_sync_state.json").write_text(raw, encoding="utf-8")
            self.assertTrue(self.due(6), raw)

    def test_mixed_timezone_awareness_falls_back_to_due(self):
        aware = datetime(2026, 11, 27, 11, 0, 0, tzinfo=timezone.utc)      # 1시간 전이지만 시간대 정보가 달라 비교 불가
        self.write_state(aware)
        self.assertTrue(self.due(6, now=NOW))

    def test_timezone_aware_state_without_now_uses_same_zone(self):
        self.write_state(datetime.now(timezone.utc) - timedelta(minutes=5))
        self.assertFalse(ms.pull_due(6, self.data))
        self.write_state(datetime.now(timezone.utc) - timedelta(hours=9))
        self.assertTrue(ms.pull_due(6, self.data))


class KeyOfTest(unittest.TestCase):
    MEMO = {"at": "2026-11-27T10:00:00", "kind": "note", "text": "발표 잘함"}

    def test_stored_server_key_is_used_as_is(self):
        memo = {**self.MEMO, "memo_key": "server-key-1"}
        self.assertEqual(ms.key_of("2026-11-27", 3, "수학", memo), "server-key-1")

    def test_computed_when_no_stored_key(self):
        self.assertEqual(ms.key_of("2026-11-27", 3, "수학", dict(self.MEMO)),
                         ms.memo_key("2026-11-27", 3, "수학", self.MEMO))

    def test_empty_or_non_string_stored_key_is_not_trusted(self):
        want = ms.memo_key("2026-11-27", 3, "수학", self.MEMO)
        for junk in ("", None, 123, ["k"], {"a": 1}):
            self.assertEqual(ms.key_of("2026-11-27", 3, "수학", {**self.MEMO, "memo_key": junk}), want, repr(junk))

    def test_stored_key_wins_even_if_memo_changed(self):
        # 서버에서 내려받은 메모는 적은 시각이 서버 쪽과 달라도 키가 바뀌면 안 된다
        memo = {**self.MEMO, "memo_key": "k", "at": "다른 시각"}
        self.assertEqual(ms.key_of("2026-11-27", 3, "수학", memo), "k")


if __name__ == "__main__":
    unittest.main()
