#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import ctypes
import sys
import time

from pywinauto import Desktop
from pywinauto.keyboard import send_keys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

TITLE = "「경북형 웍스 AI」 활용 우수 사례 공모전 신청서 제출(에이전트 부문)"
BODY = (
    "1. 관련: 미래교육정보과-15666(2026. 10. 11.)\n"
    "2. 「경북형 웍스 AI」 활용 우수 사례 공모전 신청서(에이전트 부문)를 붙임과 같이 제출하고자 합니다.\n"
    "\n"
    "붙임  공모 신청서(에이전트 부문) 1부.  끝."
)

CF_UNICODETEXT = 13
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


def set_clipboard_text(text: str) -> bool:
    if not user32.OpenClipboard(None):
        return False
    user32.EmptyClipboard()
    encoded = text.encode("utf-16le") + b"\x00\x00"
    h_mem = kernel32.GlobalAlloc(0x0042, len(encoded))
    p_mem = kernel32.GlobalLock(h_mem)
    ctypes.memmove(p_mem, encoded, len(encoded))
    kernel32.GlobalUnlock(h_mem)
    user32.SetClipboardData(CF_UNICODETEXT, h_mem)
    user32.CloseClipboard()
    return True


def find_win():
    desk = Desktop(backend="uia")
    for w in desk.windows():
        if "표준서식" in (w.window_text() or ""):
            return w
    return None


def find_by_auto(win, auto_id, control_type=None):
    for c in win.descendants():
        try:
            info = c.element_info
            if (info.automation_id or "") == auto_id:
                if control_type is None or info.control_type == control_type:
                    return c
        except Exception:
            continue
    return None


def find_by_name_type(win, name, control_type):
    for c in win.descendants():
        try:
            info = c.element_info
            if (info.name or "") == name and info.control_type == control_type:
                return c
        except Exception:
            continue
    return None


def dump_taskcard(win):
    print("--- 과제카드/공개/수신 주변 ---")
    for c in win.descendants():
        try:
            info = c.element_info
            name = info.name or ""
            auto = info.automation_id or ""
            ctl = info.control_type or ""
            if any(k in name or k in auto for k in ["과제", "Tkcrd", "tkcrd", "공개", "열람", "수신", "내부결재", "교육청"]):
                val = ""
                try:
                    val = (c.get_value() or "")[:100]
                except Exception:
                    pass
                print(f"  {ctl} name={name!r} auto={auto!r} val={val!r} {c.rectangle()}")
        except Exception:
            continue


def main():
    win = find_win()
    if not win:
        print("WXSClient 기안 창을 찾지 못했습니다.")
        sys.exit(1)
    print("window", win.window_text(), win.rectangle())
    try:
        win.set_focus()
    except Exception as e:
        print("focus", e)
    dump_taskcard(win)

    sj = find_by_auto(win, "Sj", "Edit") or find_by_name_type(win, "제목", "Edit")
    print("Sj", sj)
    if sj:
        sj.click_input()
        time.sleep(0.2)
        send_keys("^a{BACKSPACE}", pause=0.02)
        time.sleep(0.1)
        if not set_clipboard_text(TITLE):
            print("clipboard title fail")
        send_keys("^v", pause=0.05)
        time.sleep(0.3)
        try:
            print("title value", sj.get_value())
        except Exception as e:
            print("title get", e)

    print("clipboard body", set_clipboard_text(BODY))
    # 본문 탭
    maindoc = find_by_auto(win, "maindoc1") or find_by_name_type(win, "본문", "Hyperlink")
    print("본문탭", maindoc)
    if maindoc:
        maindoc.click_input()
        time.sleep(1.5)

    # 본문 영역 클릭 후 붙여넣기: 창 중앙 하단 쪽
    r = win.rectangle()
    cx = r.left + int(r.width() * 0.5)
    cy = r.top + int(r.height() * 0.62)
    print("click body approx", cx, cy)
    from pywinauto.mouse import click
    click(button="left", coords=(cx, cy))
    time.sleep(0.4)
    set_clipboard_text(BODY)
    send_keys("^v", pause=0.05)
    print("pasted body")

    # 다시 결재정보 탭으로 돌아가 과제카드 확인
    prop = find_by_auto(win, "property")
    if prop:
        prop.click_input()
        time.sleep(0.8)
        dump_taskcard(win)


if __name__ == "__main__":
    main()
