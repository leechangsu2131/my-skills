#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Save 문서관리카드 body/attachments then inspect 문서처리."""
import sys
import time
from pathlib import Path

from pywinauto import Desktop
from pywinauto.keyboard import send_keys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

DEST = Path(r"C:\Users\user\Downloads\공문")
DEST.mkdir(parents=True, exist_ok=True)


def desk():
    return Desktop(backend="uia")


def wins_named(substr):
    return [w for w in desk().windows() if substr in (w.window_text() or "")]


def dump_win(win, limit=80):
    print("WINDOW", win.window_text(), win.rectangle())
    n = 0
    for c in win.descendants():
        info = c.element_info
        name = info.name or ""
        auto = info.automation_id or ""
        ctl = info.control_type or ""
        r = c.rectangle()
        if r.width() < 6 or r.height() < 6:
            continue
        if not (name or auto):
            continue
        print(f"  {ctl:12} auto={auto!r:20} name={name!r} {r}")
        n += 1
        if n >= limit:
            break


def find_by_auto(win, auto_id):
    for c in win.descendants():
        if (c.element_info.automation_id or "") == auto_id:
            return c
    return None


def find_by_name(win, name, control_type=None):
    for c in win.descendants():
        info = c.element_info
        if (info.name or "") == name:
            if control_type is None or info.control_type == control_type:
                return c
    return None


def handle_save_dialog(timeout=8):
    t0 = time.time()
    while time.time() - t0 < timeout:
        for w in desk().windows():
            t = w.window_text() or ""
            if any(k in t for k in ("다른 이름으로 저장", "저장", "Save As", "폴더 찾아보기", "파일 다운로드")):
                if "문서관리카드" in t:
                    continue
                print("SAVE DLG", t, w.rectangle())
                dump_win(w, limit=40)
                try:
                    w.set_focus()
                except Exception:
                    pass
                # Try address bar / filename
                # Alt+D then type dest, Enter, then Alt+S
                send_keys("%d")
                time.sleep(0.3)
                send_keys(str(DEST).replace(" ", "{SPACE}"), with_spaces=True, pause=0.02)
                send_keys("{ENTER}")
                time.sleep(0.6)
                send_keys("%s")
                time.sleep(0.8)
                # If still open, press Enter
                still = [x for x in desk().windows() if (x.window_text() or "") == t]
                if still:
                    send_keys("{ENTER}")
                    time.sleep(0.5)
                return t
        time.sleep(0.3)
    print("NO SAVE DIALOG")
    return None


def main():
    hits = wins_named("문서관리카드")
    if not hits:
        print("NO DOCCARD")
        return
    win = hits[0]
    try:
        win.set_focus()
    except Exception as e:
        print("focus", e)
    time.sleep(0.4)

    # 1) 본문 탭
    body = find_by_auto(win, "maindoc1")
    print("본문 tab", body)
    if body:
        body.click_input()
        time.sleep(1.0)

    # 2) 상단 PC저장
    pc_top = find_by_name(win, "PC저장(새창열기)")
    print("PC저장 top", pc_top)
    if pc_top:
        pc_top.click_input()
        time.sleep(1.2)
        handle_save_dialog()

    # 3) 첨부 전체 체크 후 PC저장
    names = [
        "1. 2026년 만족도 조사 대상 학교 명단(경북).xlsx",
        "2. 2026년도 학생선수 e-School 만족도조사 참여 방법.hwpx",
        "3. 배너 및 팝업.zip",
        "4. 가정통신문(예시).hwpx",
    ]
    for nm in names:
        cb = find_by_name(win, nm, "CheckBox")
        print("chk", nm, cb)
        if cb:
            try:
                if cb.get_toggle_state() == 0:
                    cb.click_input()
                    time.sleep(0.2)
            except Exception:
                cb.click_input()
                time.sleep(0.2)

    btn = find_by_auto(win, "btnAttSave")
    print("btnAttSave", btn)
    if btn:
        btn.click_input()
        time.sleep(1.2)
        handle_save_dialog(timeout=12)

    print("DEST files after save:")
    for p in DEST.glob("*"):
        print(" ", p.name, p.stat().st_size)

    # 4) 문서처리 탭 클릭 후 UI dump
    proc = find_by_auto(win, "processdoc")
    print("문서처리", proc)
    if proc:
        proc.click_input()
        time.sleep(1.5)
        dump_win(win, limit=90)

    print("ALL WINDOWS now:")
    for w in desk().windows():
        t = w.window_text() or ""
        if t.strip() and w.rectangle().width() > 50:
            print(" ", repr(t[:80]), w.rectangle())


if __name__ == "__main__":
    main()
