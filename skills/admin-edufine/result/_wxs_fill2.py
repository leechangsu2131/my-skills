#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import time

import win32clipboard
import win32con
from pywinauto import Desktop
from pywinauto.keyboard import send_keys
from pywinauto.mouse import click

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

TITLE = "「경북형 웍스 AI」 활용 우수 사례 공모전 신청서 제출(에이전트 부문)"
BODY = (
    "1. 관련: 미래교육정보과-15666(2026. 10. 11.)\r\n"
    "2. 「경북형 웍스 AI」 활용 우수 사례 공모전 신청서(에이전트 부문)를 붙임과 같이 제출하고자 합니다.\r\n"
    "\r\n"
    "붙임  공모 신청서(에이전트 부문) 1부.  끝."
)


def set_clip(text, retries=5):
    last = None
    for i in range(retries):
        try:
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
            finally:
                win32clipboard.CloseClipboard()
            return True
        except Exception as e:
            last = e
            time.sleep(0.2)
    print("clipboard fail", last)
    return False


def find_win():
    desk = Desktop(backend="uia")
    for w in desk.windows():
        if "표준서식" in (w.window_text() or ""):
            return w
    return None


def find_auto(win, auto_id, control_type=None):
    for c in win.descendants():
        try:
            info = c.element_info
            if (info.automation_id or "") == auto_id:
                if control_type is None or info.control_type == control_type:
                    return c
        except Exception:
            continue
    return None


def main():
    win = find_win()
    print("win", win.window_text() if win else None)
    win.set_focus()
    time.sleep(0.2)

    sj = find_auto(win, "Sj", "Edit")
    print("sj", sj, "val", sj.get_value() if sj else None)
    if sj:
        set_clip(TITLE)
        sj.click_input()
        time.sleep(0.2)
        send_keys("^a", pause=0.03)
        time.sleep(0.1)
        set_clip(TITLE)
        send_keys("^v", pause=0.05)
        time.sleep(0.4)
        print("title now", sj.get_value())

    # 본문 탭
    tab = find_auto(win, "maindoc1")
    print("tab", tab)
    if tab:
        tab.click_input()
        time.sleep(2.0)

    r = win.rectangle()
    cx = r.left + int(r.width() * 0.52)
    cy = r.top + int(r.height() * 0.58)
    print("body click", cx, cy)
    click(button="left", coords=(cx, cy))
    time.sleep(0.5)
    set_clip(BODY)
    send_keys("^a", pause=0.03)
    time.sleep(0.1)
    set_clip(BODY)
    send_keys("^v", pause=0.05)
    print("body pasted")
    time.sleep(0.5)

    # 결재정보로 복귀
    prop = find_auto(win, "property")
    if prop:
        prop.click_input()
        time.sleep(1.0)
    sj2 = find_auto(win, "Sj", "Edit")
    print("title after", sj2.get_value() if sj2 else None)


if __name__ == "__main__":
    main()
