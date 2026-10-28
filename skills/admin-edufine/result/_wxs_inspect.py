#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import ctypes
import ctypes.wintypes as wt
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)

GetWindowTextW = user32.GetWindowTextW
GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
GetWindowTextLengthW = user32.GetWindowTextLengthW
GetClassNameW = user32.GetClassNameW
GetClassNameW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
IsWindowVisible = user32.IsWindowVisible
GetWindowRect = user32.GetWindowRect

windows = []

def text_of(hwnd):
    n = GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(n + 2)
    GetWindowTextW(hwnd, buf, n + 2)
    return buf.value

def class_of(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    GetClassNameW(hwnd, buf, 256)
    return buf.value

def rect_of(hwnd):
    r = wt.RECT()
    GetWindowRect(hwnd, ctypes.byref(r))
    return (r.left, r.top, r.right, r.bottom)

@WNDENUMPROC
def enum_top(hwnd, lparam):
    cls = class_of(hwnd)
    title = text_of(hwnd)
    vis = bool(IsWindowVisible(hwnd))
    if vis and ("WXS" in cls or "표준서식" in title or "기안" in title or "결재" in title or "HCLT" in title or "Afx" in cls):
        windows.append((hwnd, cls, title, rect_of(hwnd)))
    if vis and title:
        # keep notable
        if any(k in title for k in ["표준", "서식", "에듀", "문서", "WXS", "한글"]):
            windows.append((hwnd, cls, title, rect_of(hwnd)))
    return True

user32.EnumWindows(enum_top, 0)
print("TOP WINDOWS:")
seen = set()
for hwnd, cls, title, rect in windows:
    if hwnd in seen:
        continue
    seen.add(hwnd)
    print(f"  hwnd={hwnd} cls={cls} title={title!r} rect={rect}")

# Enum children of WXSClient-like
target = None
for hwnd, cls, title, rect in windows:
    if "표준서식" in title:
        target = hwnd
        break

if not target:
    print("No target")
    sys.exit(0)

print("\nCHILDREN of", target)
children = []

@WNDENUMPROC
def enum_child(hwnd, lparam):
    children.append((hwnd, class_of(hwnd), text_of(hwnd), rect_of(hwnd), bool(IsWindowVisible(hwnd))))
    return True

user32.EnumChildWindows(target, enum_child, 0)
print(f"count={len(children)}")
for hwnd, cls, title, rect, vis in children:
    if not vis and not title:
        continue
    w = rect[2] - rect[0]
    h = rect[3] - rect[1]
    if w < 20 or h < 8:
        continue
    print(f"  vis={vis} hwnd={hwnd} cls={cls} title={title!r} size={w}x{h} pos={rect}")
