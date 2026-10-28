#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import time
from pathlib import Path

from pywinauto import Desktop
from pywinauto.keyboard import send_keys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

DEST = Path(r"C:\Users\user\Downloads\공문")


def main():
    desk = Desktop(backend="uia")
    hits = [w for w in desk.windows() if "문서관리카드" in (w.window_text() or "")]
    if not hits:
        print("NO CARD")
        return
    win = hits[0]
    try:
        win.set_focus()
    except Exception as e:
        print("focus", e)

    print("=== ALL CONTROLS with 본문/첨부/확인/체크/배포/비배포 ===")
    cbs = []
    confirm = None
    for c in win.descendants():
        info = c.element_info
        name = info.name or ""
        auto = info.automation_id or ""
        ctl = info.control_type or ""
        r = c.rectangle()
        blob = name + " " + auto + " " + ctl
        if any(k in blob for k in ("본문", "첨부", "확인", "배포", "비배포", "CheckBox", "checkbox", "파일구분", "문서형식")):
            print(f"{ctl:12} auto={auto!r:20} name={name!r} {r}")
        if ctl == "CheckBox":
            cbs.append(c)
            print(" CHECKBOX", name, r)
        if name == "확인" and ctl in ("Hyperlink", "Button", "ListItem") and r.top > 300 and r.top < 420:
            confirm = c

    print("checkboxes", len(cbs), "confirm", confirm)
    for cb in cbs:
        nm = cb.element_info.name or ""
        print(" toggle", nm)
        try:
            st = cb.get_toggle_state()
            print("  state", st)
            if st == 0:
                cb.click_input()
                time.sleep(0.15)
        except Exception as e:
            print("  toggle err", e)
            try:
                cb.click_input()
            except Exception as e2:
                print("  click err", e2)

    # click 본문 / 첨부파일 texts if they are actually checkboxes represented as text
    for label in ("본문", "첨부파일", "배포(PDF 형식)", "비배포(ODT 형식)"):
        els = [c for c in win.descendants() if (c.element_info.name or "") == label]
        print("label", label, len(els), [c.element_info.control_type for c in els[:5]])

    if confirm is None:
        for c in win.descendants():
            if (c.element_info.name or "") == "확인" and c.element_info.control_type == "Hyperlink":
                r = c.rectangle()
                if r.top < 400:
                    confirm = c
                    break
    print("click confirm", confirm)
    if confirm:
        confirm.click_input()
        time.sleep(1.5)

    print("=== windows after confirm ===")
    for w in desk.windows():
        t = w.window_text() or ""
        if t.strip() and w.rectangle().width() > 80:
            print(repr(t[:90]), w.rectangle())

    # Handle Windows folder picker / save
    time.sleep(0.5)
    for w in desk.windows():
        t = w.window_text() or ""
        if any(k in t for k in ("다른 이름으로 저장", "폴더 찾아보기", "찾아보기", "Save As", "파일 저장", "저장 위치")):
            print("OS DLG", t)
            w.set_focus()
            time.sleep(0.2)
            send_keys("%n")  # 파일 이름
            time.sleep(0.2)
            send_keys("^a")
            send_keys(str(DEST), with_spaces=True, pause=0.01)
            send_keys("{ENTER}")
            time.sleep(0.8)
            send_keys("%s")
            time.sleep(0.5)
            send_keys("{ENTER}")

    time.sleep(2)
    print("NEW FILES:")
    for p in sorted(DEST.glob("*"), key=lambda x: x.stat().st_mtime, reverse=True)[:15]:
        print(" ", time.strftime("%H:%M:%S", time.localtime(p.stat().st_mtime)), p.name, p.stat().st_size)


if __name__ == "__main__":
    main()
