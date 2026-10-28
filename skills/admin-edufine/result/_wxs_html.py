#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read WXSClient embedded IE HTML via WM_HTML_GETOBJECT."""
import ctypes
import ctypes.wintypes as wt
import sys

import comtypes
import comtypes.client
from comtypes.automation import IDispatch

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

user32 = ctypes.windll.user32
oleacc = ctypes.oledll.oleacc

WM_HTML_GETOBJECT = user32.RegisterWindowMessageW("WM_HTML_GETOBJECT")
SMTO_ABORTIFHUNG = 0x0002

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)

GetClassNameW = user32.GetClassNameW
GetClassNameW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
GetWindowTextW = user32.GetWindowTextW
GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
GetWindowTextLengthW = user32.GetWindowTextLengthW

def class_of(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    GetClassNameW(hwnd, buf, 256)
    return buf.value

def text_of(hwnd):
    n = GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(n + 2)
    GetWindowTextW(hwnd, buf, n + 2)
    return buf.value

top = []

@WNDENUMPROC
def enum_top(hwnd, lparam):
    if user32.IsWindowVisible(hwnd) and "표준서식" in text_of(hwnd):
        top.append(hwnd)
    return True

user32.EnumWindows(enum_top, 0)
print("top", top)
if not top:
    sys.exit(1)

ie_hwnd = []

@WNDENUMPROC
def enum_child(hwnd, lparam):
    if class_of(hwnd) == "Internet Explorer_Server":
        ie_hwnd.append(hwnd)
    return True

user32.EnumChildWindows(top[0], enum_child, 0)
print("ie", ie_hwnd)
if not ie_hwnd:
    sys.exit(1)

hwnd = ie_hwnd[0]
lresult = wt.LPARAM()
ok = user32.SendMessageTimeoutW(hwnd, WM_HTML_GETOBJECT, 0, 0, SMTO_ABORTIFHUNG, 5000, ctypes.byref(lresult))
print("send", ok, lresult.value)

IID_IHTMLDocument2 = comtypes.GUID("{332C4425-26CB-11D0-B483-00C04FD90119}")
doc_ptr = ctypes.POINTER(IDispatch)()
oleacc.ObjectFromLresult(lresult.value, ctypes.byref(IID_IHTMLDocument2), 0, ctypes.byref(doc_ptr))
doc = doc_ptr
# wrap as COM
html = comtypes.client.GetBestInterface(doc)
print("title", html.title)
print("url", html.url)
body = html.body
print("body tag", body.tagName)

# dump inputs of interest
script = html.parentWindow
# use document.all
all_el = html.all
ids = ["Sj", "sj", "title", "pass", "IDC_SENDER_NAMES", "recpList", "aChooseTkcrd"]
info = []
count = all_el.length
print("all length", count)
interesting = []
for i in range(min(count, 800)):
    try:
        el = all_el.item(i)
        tag = (el.tagName or "").upper()
        eid = el.getAttribute("id") or ""
        name = el.getAttribute("name") or ""
        typ = el.getAttribute("type") or ""
        val = ""
        try:
            val = el.getAttribute("value") or ""
        except Exception:
            pass
        txt = ""
        try:
            txt = (el.innerText or "")[:80]
        except Exception:
            pass
        if tag in ("INPUT", "SELECT", "TEXTAREA", "BUTTON", "A") or eid in ("Sj", "pass"):
            interesting.append({"tag": tag, "id": eid, "name": name, "type": typ, "value": str(val)[:120], "text": txt})
    except Exception:
        continue

print("interesting", len(interesting))
for x in interesting:
    if any(k in (x["id"] + x["name"] + x["text"] + x["value"]).lower() for k in [
        "sj", "title", "제목", "과제", "tkcrd", "공개", "수신", "본문", "hwp", "editor", "format", "sanctn", "기안"
    ]) or x["tag"] in ("SELECT", "TEXTAREA"):
        print(x)
