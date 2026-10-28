#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
from pywinauto import Desktop

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


def main():
    desk = Desktop(backend="uia")
    hits = [w for w in desk.windows() if "문서관리카드" in (w.window_text() or "")]
    print("hits", [(w.window_text(), w.rectangle()) for w in hits])
    if not hits:
        return
    win = hits[0]
    try:
        win.set_focus()
    except Exception as e:
        print("focus", e)
    n = 0
    for c in win.descendants():
        info = c.element_info
        name = info.name or ""
        auto = info.automation_id or ""
        ctl = info.control_type or ""
        cls = info.class_name or ""
        r = c.rectangle()
        val = ""
        try:
            val = (c.get_value() or "")[:80]
        except Exception:
            pass
        if r.width() < 6 or r.height() < 6:
            continue
        keep = ctl in ("Button", "Hyperlink", "Edit", "Document", "DataItem", "ListItem", "TreeItem", "TabItem", "CheckBox", "ComboBox", "Text") or auto or name
        if keep and (name or auto or val):
            print(f"{ctl:12} auto={auto!r:24} name={name!r:50} val={val!r} {r} cls={cls!r}")
            n += 1
            if n >= 120:
                break


if __name__ == "__main__":
    main()
