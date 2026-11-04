"""Non-destructive GBTalk received-note capture without the Computer Use `sky` client.

Reads the currently selected row of 쪽지관리함 > 받은쪽지함, then sends only `Down`.
Body: UIA Value of RICHEDIT50W (automation id 1022). Sender/date/time are NOT exposed
through pywinauto UIA, so a full window screenshot is saved per row for visual review.

Usage (Windows, pywinauto + Pillow + pywin32):
  set CLICK_XY=<x>,<y>   (optional: click the already-selected row to focus the list)
  set RESUME=1           (optional: continue an existing rows.jsonl)
  python capture_pywinauto.py <manager-hwnd> <out-dir> <max-rows> <baseline-raw.jsonl> [start-seq]

Stops on: manager not foreground, list not focused, no (body, header) change after Down,
max rows, or a whitespace-normalized body equal to one of the first 3 baseline rows
(boundary candidate; confirm its header visually before declaring completion).
"""
import ctypes
import hashlib
import json
import os
import re
import sys
import time

import win32gui
from PIL import ImageGrab
from pywinauto import Desktop, keyboard

sys.stdout.reconfigure(encoding="utf-8")
ctypes.windll.user32.SetProcessDPIAware()

HWND = int(sys.argv[1])
OUT = sys.argv[2]
MAX_ROWS = int(sys.argv[3])
BASELINE = sys.argv[4]
START_SEQ = int(sys.argv[5]) if len(sys.argv) > 5 else 1
HEADER_BOX = (650, 85, 1300, 180)  # window-relative header area at the observed window size
os.makedirs(OUT, exist_ok=True)


def norm(text):
    return re.sub(r"\s+", " ", text or "").strip()


baseline = []
with open(BASELINE, encoding="utf-8") as handle:
    for line in handle:
        if line.strip():
            record = json.loads(line)
            baseline.append((norm(record["body"]), record.get("received_date"), record.get("sender"), record["sequence"]))
            if len(baseline) >= 3:
                break

win = Desktop(backend="uia").window(handle=HWND).wrapper_object()


def find(pred):
    for element in win.descendants():
        if pred(element.element_info):
            return element
    return None


def list_has_focus():
    lst = find(lambda e: e.class_name == "UltariListScrollView")
    try:
        return bool(lst and lst.element_info.element.CurrentHasKeyboardFocus)
    except Exception:
        return False


def read_body():
    edit = find(lambda e: e.class_name == "RICHEDIT50W" and e.automation_id == "1022")
    return None if edit is None else edit.iface_value.CurrentValue


def state():
    img = ImageGrab.grab(bbox=win32gui.GetWindowRect(HWND), all_screens=True)
    header_sha = hashlib.sha256(img.crop(HEADER_BOX).tobytes()).hexdigest()
    return read_body(), header_sha, img


def stable(prev=None, tries=20):
    # Adjacent notes can share an identical header (same sender and minute), so a move
    # is accepted when the (body, header) pair changes and is then read twice in a row.
    last = None
    for _ in range(tries):
        body, header, img = state()
        if body is not None and (prev is None or (body, header) != prev):
            if last == (body, header):
                return body, header, img
            last = (body, header)
        time.sleep(0.35)
    return None


if os.environ.get("CLICK_XY"):
    from pywinauto import mouse
    x, y = map(int, os.environ["CLICK_XY"].split(","))
    mouse.click(coords=(x, y))
    time.sleep(0.8)

rows_path = os.path.join(OUT, "rows.jsonl")
log = open(rows_path, "a", encoding="utf-8")
seq = START_SEQ
cur = stable()
if cur is None:
    print("STOP unstable-initial")
    sys.exit(2)
skip_current = False
if os.environ.get("RESUME"):
    last = [json.loads(l) for l in open(rows_path, encoding="utf-8") if l.strip()][-1]
    skip_current = cur[0] == last["body"] and cur[1] == last["header_sha256"]
    print("RESUME", "current==last saved" if skip_current else "saving current as next", flush=True)
    seq = last["sequence"] + 1
saved = 0
while True:
    body, header, img = cur
    if skip_current:
        skip_current = False
    else:
        img.convert("RGB").save(os.path.join(OUT, f"row-{seq:04d}.jpg"), quality=80)
        match = [b for b in baseline if b[0] == norm(body)]
        if match:
            print("STOP boundary-candidate", seq, match[0][1:], flush=True)
            break
        record = {"sequence": seq, "body": body, "body_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
                  "header_sha256": header, "screenshot": f"row-{seq:04d}.jpg"}
        log.write(json.dumps(record, ensure_ascii=False) + "\n")
        log.flush()
        os.fsync(log.fileno())
        print("SAVED", seq, norm(body)[:60], flush=True)
        saved += 1
        seq += 1
        if saved >= MAX_ROWS:
            print("STOP max-rows", flush=True)
            break
    if win32gui.GetForegroundWindow() != HWND:
        print("STOP not-foreground", flush=True)
        break
    if not list_has_focus():
        print("STOP list-not-focused", flush=True)
        break
    keyboard.send_keys("{DOWN}")
    nxt = stable(prev=(body, header))
    if nxt is None:
        print("STOP no-change-after-down", flush=True)
        break
    cur = nxt
log.close()
