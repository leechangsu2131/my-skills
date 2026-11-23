"""cmd_morning 통합 시험: 카카오·시트는 가짜로 바꾸고 무엇이 누구에게 가는지 본다."""
import argparse

import pytest

from schooltodo import cli

DAY = "2026-11-16"  # 월요일(주간 출장 메시지 보내는 날)
ROWS = [
    {"키": "a", "날짜": DAY, "구분": "학교", "내용": "체육대회", "상태": "", "출처": "수동", "대상": "3학년"},
    {"키": "b", "날짜": DAY, "구분": "개인", "내용": "선생님 개인 할 일", "상태": "", "출처": "수동", "대상": "3학년"},
    {"키": "c", "날짜": "2026-11-18", "구분": "출장", "내용": "교육청 연수", "상태": "", "출처": "수동", "대상": "3학년"},
]


class FakeRecipients:
    def __init__(self, rows, write_error=None):
        self._rows = rows
        self.write_error = write_error

    def rows(self):
        return [dict(r) for r in self._rows]

    def write(self, changes):
        if self.write_error:
            raise self.write_error


class FakeShare:
    def __init__(self):
        self.saved = {}

    def values(self):
        return {"WEBAPP_URL": "https://x/exec", "VIEW_TOKEN": "T", **self.saved}

    def save(self, updates):
        self.saved.update(updates)


class FakeDb:
    def __init__(self, recipients, share=None):
        self._rec = recipients
        self._share = share or FakeShare()

    def rows(self):
        return [dict(r) for r in ROWS]

    def recipients(self):
        return self._rec

    def share_tab(self):
        return self._share


@pytest.fixture
def sent(monkeypatch):
    log = {"memo": [], "friends": []}
    monkeypatch.setattr(cli, "refresh_access_token", lambda *a, **k: "AT")
    monkeypatch.setattr(cli, "_adopt_new_refresh_token", lambda f: None)
    monkeypatch.setattr(cli, "send_memo", lambda t, text, link, *a, **k: log["memo"].append(text))
    monkeypatch.setattr(
        cli, "send_friends", lambda t, uuids, text, link, button_title="": log["friends"].append((list(uuids), text, link))
    )
    monkeypatch.setattr(cli.time, "sleep", lambda s: None)
    for k in ("KAKAO_FRIEND_UUIDS", "WEEKLY_FRIEND_UUIDS", "WEEKLY_DAY", "KAKAO_SEND_TO_ME", "SKIP_IF_EMPTY", "SYNC_FAILED", "MESSAGE_LINK_URL"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("KAKAO_REST_API_KEY", "K")
    monkeypatch.setenv("KAKAO_REFRESH_TOKEN", "R")
    monkeypatch.setenv("DB_SHEET_ID", "S")
    return log


def run(monkeypatch, db):
    monkeypatch.setattr(cli, "_open_db", lambda args: db)
    args = argparse.Namespace(today=DAY, weekly=False, dry_run=False, db_csv=None)
    return cli.cmd_morning(args)


def test_my_message_goes_even_if_recipient_lookup_and_sheet_fail(monkeypatch, sent):
    def boom(token):
        raise ConnectionError("network down")

    monkeypatch.setattr(cli, "list_friends", boom)
    rec = FakeRecipients([{"_row": 2, "이름": "", "받기": "매일", "카카오ID": "1", "uuid": ""}], write_error=RuntimeError("quota"))
    assert run(monkeypatch, FakeDb(rec)) == 0
    assert sent["memo"], "선생님 메시지는 가야 한다"
    assert sent["friends"] == []


def test_my_message_goes_even_if_friend_send_and_share_tab_fail(monkeypatch, sent):
    def bad_send(*a, **k):
        raise TimeoutError("slow")

    class BadShare(FakeShare):
        def save(self, updates):
            raise RuntimeError("sheet write failed")

    monkeypatch.setattr(cli, "send_friends", bad_send)
    rec = FakeRecipients([{"_row": 2, "이름": "엄마", "받기": "매일", "카카오ID": "1", "uuid": "U1"}])
    assert run(monkeypatch, FakeDb(rec, BadShare())) == 0
    assert sent["memo"]


def test_friend_gets_one_message_without_personal_tasks_and_view_link(monkeypatch, sent):
    rec = FakeRecipients([{"_row": 2, "이름": "엄마", "받기": "매일", "카카오ID": "1", "uuid": "U1"}])
    share = FakeShare()
    run(monkeypatch, FakeDb(rec, share))
    assert len(sent["friends"]) == 1
    uuids, text, link = sent["friends"][0]
    assert uuids == ["U1"] and "체육대회" in text and "개인 할 일" not in text
    assert link == "https://x/exec?view=T&k=daily"
    assert "개인 할 일" not in share.saved["DAILY_TEXT"] and "DAILY_UPDATED" in share.saved


def test_daily_receiver_does_not_get_weekly_too_on_same_day(monkeypatch, sent):
    monkeypatch.setenv("WEEKLY_FRIEND_UUIDS", "U1,U2")
    rec = FakeRecipients([{"_row": 2, "이름": "엄마", "받기": "매일", "카카오ID": "1", "uuid": "U1"}])
    run(monkeypatch, FakeDb(rec))
    receivers = [u for uuids, _, _ in sent["friends"] for u in uuids]
    assert receivers.count("U1") == 1 and "U2" in receivers
    weekly = [t for uuids, t, link in sent["friends"] if link.endswith("k=weekly")]
    assert weekly and "교육청 연수" in weekly[0]


def test_no_friend_targets_only_waiting_does_not_fail(monkeypatch, sent):
    monkeypatch.setenv("KAKAO_SEND_TO_ME", "0")
    monkeypatch.setattr(cli, "list_friends", lambda token: [])
    rec = FakeRecipients([{"_row": 2, "이름": "", "받기": "주간출장", "카카오ID": "9", "uuid": ""}])
    assert run(monkeypatch, FakeDb(rec)) == 0
    assert sent["memo"] == [] and sent["friends"] == []
