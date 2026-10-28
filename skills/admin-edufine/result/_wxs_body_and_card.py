#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import time

from pywinauto import Desktop

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


def find_win(substr):
    desk = Desktop(backend="uia")
    hits = []
    for w in desk.windows():
        t = w.window_text() or ""
        if substr in t:
            hits.append(w)
    return hits


def dump(win, limit=80):
    print("WINDOW", win.window_text(), win.rectangle())
    n = 0
    for c in win.descendants():
        info = c.element_info
        name = info.name or ""
        auto = info.automation_id or ""
        ctl = info.control_type or ""
        cls = info.class_name or ""
        r = c.rectangle()
        if r.width() < 10 or r.height() < 8:
            continue
        val = ""
        try:
            val = (c.get_value() or "")[:60]
        except Exception:
            pass
        keep = ctl in ("Edit", "Document", "Button", "ComboBox", "DataItem", "Hyperlink", "ListItem", "Table", "CheckBox", "RadioButton") or auto or ("과제" in name) or ("본문" in name) or ("검색" in name) or ("확인" in name) or ("한글" in name)
        if keep:
            print(f"  {ctl:12} auto={auto!r:20} name={name!r:40} val={val!r} {r} cls={cls!r}")
            n += 1
            if n >= limit:
                break


def find_auto(win, auto_id, control_type=None):
    for c in win.descendants():
        info = c.element_info
        if (info.automation_id or "") == auto_id:
            if control_type is None or info.control_type == control_type:
                return c
    return None


def main():
    wins = find_win("표준서식")
    print("draft wins", [w.window_text() for w in wins])
    if not wins:
        return
    win = wins[0]
    win.set_focus()

    # 본문 탭 클릭 후 컨트롤
    tab = find_auto(win, "maindoc1")
    print("click 본문", tab)
    if tab:
        tab.click_input()
        time.sleep(2.2)
    print("=== AFTER 본문 TAB ===")
    dump(win, limit=60)

    # 결재정보 복귀 후 과제카드 선택
    prop = find_auto(win, "property")
    if prop:
        prop.click_input()
        time.sleep(1.0)
    choose = find_auto(win, "aChooseTkcrd")
    print("click 과제카드", choose)
    if choose:
        choose.click_input()
        time.sleep(2.5)

    print("=== ALL WINDOWS after card click ===")
    desk = Desktop(backend="uia")
    for w in desk.windows():
        t = w.window_text() or ""
        if not t:
            continue
        if any(k in t for k in ["과제", "카드", "표준서식", "검색", "조직", "수신", "선택"]):
            print(" WIN", t, w.rectangle())

    cards = find_win("과제") + find_win("카드")
    seen = set()
    for w in cards:
        if w.handle in seen:
            continue
        seen.add(w.handle)
        print("=== CARD WIN ===")
        dump(w, limit=80)


if __name__ == "__main__":
    main()
