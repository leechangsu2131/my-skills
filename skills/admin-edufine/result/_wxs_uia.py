#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
from pywinauto import Desktop

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

desk = Desktop(backend="uia")
wins = [w for w in desk.windows() if "표준서식" in (w.window_text() or "")]
print("wins", len(wins), [w.window_text() for w in wins])
if not wins:
    sys.exit(0)
w = wins[0]
print("rect", w.rectangle())
desc = w.descendants()
print("descendants", len(desc))
for c in desc:
    try:
        info = c.element_info
        name = info.name or ""
        ctl = info.control_type or ""
        auto = info.automation_id or ""
        cls = info.class_name or ""
        r = c.rectangle()
        val = ""
        try:
            val = (c.get_value() or "")[:80]
        except Exception:
            pass
        if ctl in ("Edit", "Document", "ComboBox", "Button", "EditControl", "Hyperlink", "Text", "Pane", "ToolBar", "MenuItem") or name or val:
            if r.width() < 8 or r.height() < 8:
                continue
            print(f"  {ctl:12} name={name!r:40} auto={auto!r:20} cls={cls!r:20} val={val!r} size={r.width()}x{r.height()} {r}")
    except Exception as e:
        print(" err", e)
