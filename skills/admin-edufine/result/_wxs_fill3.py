#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import time
from pathlib import Path

import win32clipboard
import win32con
import win32gui
import win32ui
from ctypes import windll
from PIL import Image
from pywinauto import Desktop
from pywinauto.keyboard import send_keys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

TITLE = "「경북형 웍스 AI」 활용 우수 사례 공모전 신청서 제출(에이전트 부문)"
BODY = (
    "1. 관련: 미래교육정보과-15666(2026. 10. 11.)\r\n"
    "2. 「경북형 웍스 AI」 활용 우수 사례 공모전 신청서(에이전트 부문)를 붙임과 같이 제출하고자 합니다.\r\n"
    "\r\n"
    "붙임  공모 신청서(에이전트 부문) 1부.  끝."
)
OUT = Path(__file__).with_name("_wxs_shot.png")


def shot(hwnd, path):
    left, top, right, bot = win32gui.GetWindowRect(hwnd)
    w, h = right - left, bot - top
    hwnd_dc = win32gui.GetWindowDC(hwnd)
    mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
    save_dc = mfc_dc.CreateCompatibleDC()
    bmp = win32ui.CreateBitmap()
    bmp.CreateCompatibleBitmap(mfc_dc, w, h)
    save_dc.SelectObject(bmp)
    result = windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 2)
    bmpinfo = bmp.GetInfo()
    bmpstr = bmp.GetBitmapBits(True)
    img = Image.frombuffer("RGB", (bmpinfo["bmWidth"], bmpinfo["bmHeight"]), bmpstr, "raw", "BGRX", 0, 1)
    img.save(path)
    win32gui.DeleteObject(bmp.GetHandle())
    save_dc.DeleteDC()
    mfc_dc.DeleteDC()
    win32gui.ReleaseDC(hwnd, hwnd_dc)
    print("shot", path, "printwindow", result, "size", w, h)


def set_clip(text):
    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
    finally:
        win32clipboard.CloseClipboard()


def find_win():
    desk = Desktop(backend="uia")
    for w in desk.windows():
        if "표준서식" in (w.window_text() or ""):
            return w
    return None


def find_auto(win, auto_id, control_type=None):
    for c in win.descendants():
        info = c.element_info
        if (info.automation_id or "") == auto_id:
            if control_type is None or info.control_type == control_type:
                return c
    return None


def main():
    win = find_win()
    hwnd = win.handle
    print("hwnd", hwnd)
    win.set_focus()
    time.sleep(0.3)

    sj = find_auto(win, "Sj", "Edit")
    print("before", repr(sj.get_value()), "legacy", getattr(sj, "legacy_properties", lambda: {})())
    # try ValuePattern
    try:
        sj.set_edit_text("")
        sj.set_edit_text(TITLE)
        print("set_edit_text ok", repr(sj.get_value()))
    except Exception as e:
        print("set_edit_text", e)

    if not (sj.get_value() or "").strip():
        sj.click_input()
        time.sleep(0.2)
        send_keys("^a{DELETE}", pause=0.02)
        time.sleep(0.1)
        send_keys(TITLE, with_spaces=True, with_tabs=False, pause=0.01, vk_packet=True)
        time.sleep(0.3)
        print("typed", repr(sj.get_value()))

    if not (sj.get_value() or "").strip():
        set_clip(TITLE)
        sj.click_input()
        time.sleep(0.15)
        send_keys("^a^v", pause=0.05)
        time.sleep(0.3)
        print("pasted", repr(sj.get_value()))

    shot(hwnd, str(OUT))


if __name__ == "__main__":
    main()
