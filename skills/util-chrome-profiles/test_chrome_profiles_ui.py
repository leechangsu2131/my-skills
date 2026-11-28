from datetime import datetime, timedelta
import sys

import pytest

pytest.importorskip("PySide6")
pytest.importorskip("win32gui")

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QApplication, QListWidgetItem, QMenu, QMessageBox

import chrome_profiles as cp


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


def _make_manager(tmp_path, monkeypatch):
    monkeypatch.setattr(cp, "CONFIG", tmp_path / "config.json")
    monkeypatch.setattr(cp.usage_pause, "store_path", lambda: tmp_path / "pauses.json")
    browser = cp.BROWSERS[0]
    monkeypatch.setattr(cp, "load_profiles", lambda: {
        "Profile 1": {"name": "계정1", "folder": "Profile 1", "browser": browser, "sid": "acct:a@example.com"},
        "Profile 2": {"name": "계정2", "folder": "Profile 2", "browser": browser, "sid": "acct:b@example.com"},
        "Profile 3": {"name": "계정3", "folder": "Profile 3", "browser": browser, "sid": "acct:c@example.com"},
    })
    monkeypatch.setattr(cp, "chrome_windows", lambda: [])
    monkeypatch.setattr(cp, "browser_render_status", lambda: {})
    monkeypatch.setattr(cp.Manager, "register_hotkeys", lambda self: None)
    monkeypatch.setattr(cp.Manager, "start_scan", lambda self: None)
    mgr = cp.Manager()
    mgr.scan_timer.stop()
    mgr.monitor_timer.stop()
    return mgr


def test_goto_dialog_default_url(qapp):
    dlg_empty = cp.GotoDialog(None, "전체", [], "tab", True, True)
    assert dlg_empty.url.currentText() == cp.DEFAULT_GOTO_URL
    assert dlg_empty.url.findText(cp.DEFAULT_GOTO_URL) >= 0

    dlg_recent = cp.GotoDialog(None, "전체", ["https://naver.com"], "tab", True, True)
    assert dlg_recent.url.currentText() == "https://naver.com"
    assert dlg_recent.url.findText(cp.DEFAULT_GOTO_URL) >= 0


def test_pause_close_button_and_action(qapp, tmp_path, monkeypatch):
    mgr = _make_manager(tmp_path, monkeypatch)
    try:
        mgr.windows = {
            101: {"key": "Profile 1", "folder": "Profile 1", "browser": "chrome", "watch": False, "last_change": 0.0, "alerted": False, "last_read": 0.0},
            102: {"key": "Profile 2", "folder": "Profile 2", "browser": "chrome", "watch": False, "last_change": 0.0, "alerted": False, "last_read": 0.0},
            103: {"key": "Profile 3", "folder": "Profile 3", "browser": "chrome", "watch": False, "last_change": 0.0, "alerted": False, "last_read": 0.0},
        }
        now_dt = datetime.now()
        future = (now_dt + timedelta(hours=1)).isoformat(timespec="minutes")
        past = (now_dt - timedelta(minutes=10)).isoformat(timespec="minutes")
        mgr.pauses = {
            "acct:a@example.com": {"resume": future, "line": "일시 중지"},
            "acct:b@example.com": {"resume": future, "line": "일시 중지"},
            "acct:c@example.com": {"resume": past, "line": "지난 시각"},
        }
        mgr.update_pause_summary(now_dt)
        assert not mgr.pause_close_button.isHidden()
        assert "일시 중지 일괄 닫기 (2)" in mgr.pause_close_button.text()
        assert mgr.paused_windows(now_dt) == [101, 102]

        closed = []
        monkeypatch.setattr(cp, "close_window", lambda hwnd: closed.append(hwnd))
        monkeypatch.setattr(QMessageBox, "question", lambda *a, **kw: QMessageBox.StandardButton.Yes)
        mgr.close_paused_windows()
        assert closed == [101, 102]

        mgr.pauses = {}
        mgr.update_pause_summary(now_dt)
        assert mgr.pause_close_button.isHidden()
    finally:
        mgr.close()


def test_tree_menu_multi_select_close(qapp, tmp_path, monkeypatch):
    mgr = _make_manager(tmp_path, monkeypatch)
    try:
        mgr.windows = {
            201: {"key": "Profile 1", "folder": "Profile 1", "browser": "chrome", "item": QListWidgetItem(), "watch": False, "last_change": 0.0, "alerted": False, "last_read": 0.0},
            202: {"key": "Profile 2", "folder": "Profile 2", "browser": "chrome", "item": QListWidgetItem(), "watch": False, "last_change": 0.0, "alerted": False, "last_read": 0.0},
        }
        items = mgr.profile_items()
        assert len(items) >= 2
        items[0].setSelected(True)
        items[1].setSelected(True)

        captured_actions = []
        closed = []
        monkeypatch.setattr(cp, "close_window", lambda hwnd: closed.append(hwnd))
        monkeypatch.setattr(QMessageBox, "question", lambda *a, **kw: QMessageBox.StandardButton.Yes)

        class FakeMenu(QMenu):
            def exec(self_menu, *_args):
                for act in self_menu.actions():
                    captured_actions.append(act.text())
                    if "고른 프로필 창 닫기" in act.text():
                        act.trigger()
                return None

        monkeypatch.setattr(cp, "QMenu", FakeMenu)
        rect = mgr.tree.visualItemRect(items[0])
        mgr.tree_menu(rect.center())

        assert any("고른 프로필 2개 열기" in t for t in captured_actions)
        assert any("고른 프로필 창 닫기 (2개)" in t for t in captured_actions)
        assert sorted(closed) == [201, 202]
    finally:
        mgr.close()
