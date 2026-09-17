#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Select a week row in 학급시간표관리.

This is a non-saving helper. It selects a row in `grdWeek` so NEIS loads that
week's `dsWeekByClsByTi` dataset.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request

from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options


APP_ID = "edu/sw/els/edc/tm/els_edctm00_m00"

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


JS_SELECT_WEEK = r"""
return (function(appId, targetDate) {
  const platform = window.cpr && cpr.core && cpr.core.Platform && cpr.core.Platform.INSTANCE;
  if (!platform) return {ok: false, error: "cpr Platform is not available"};

  const app = platform.getAllRunningAppInstances().find(function(ai) {
    return ai && ai.app && ai.app.id === appId;
  });
  if (!app) return {ok: false, error: "학급시간표관리 app is not open"};

  const ds = app.lookup("dsWeekList");
  const grid = app.lookup("grdWeek");
  if (!ds || !ds.getRowCount) return {ok: false, error: "dsWeekList not found"};
  if (!grid) return {ok: false, error: "grdWeek not found"};

  function cleanDate(value) {
    return String(value || "").replace(/[^0-9]/g, "");
  }

  let rowIndex = -1;
  let week = null;
  for (let r = 0; r < ds.getRowCount(); r++) {
    const begin = cleanDate(ds.getValue(r, "weekBgngYmd"));
    const end = cleanDate(ds.getValue(r, "weekEndYmd"));
    if (begin && end && begin <= targetDate && targetDate <= end) {
      rowIndex = r;
      week = {
        rowIndex: r,
        weekCnt: ds.getValue(r, "weekCnt"),
        weekCntNm: ds.getValue(r, "weekCntNm"),
        weekBgngYmd: ds.getValue(r, "weekBgngYmd"),
        weekEndYmd: ds.getValue(r, "weekEndYmd"),
        event: ds.getValue(r, "event")
      };
      break;
    }
  }
  if (rowIndex < 0) return {ok: false, error: "target week not found", rowCount: ds.getRowCount()};

  const attempts = [];
  function attempt(name, fn) {
    try {
      fn();
      attempts.push({name: name, ok: true});
    } catch(e) {
      attempts.push({name: name, ok: false, error: e.message});
    }
  }

  attempt("selectRows", function() {
    if (typeof grid.selectRows !== "function") throw new Error("missing");
    grid.selectRows([rowIndex]);
  });
  attempt("selectRow", function() {
    if (typeof grid.selectRow !== "function") throw new Error("missing");
    grid.selectRow(rowIndex);
  });
  attempt("focusCell", function() {
    if (typeof grid.focusCell !== "function") throw new Error("missing");
    grid.focusCell(rowIndex, 0);
  });
  attempt("setEditRowIndex", function() {
    if (typeof grid.setEditRowIndex !== "function") throw new Error("missing");
    grid.setEditRowIndex(rowIndex);
  });
  attempt("redraw", function() {
    if (typeof grid.redraw !== "function") throw new Error("missing");
    grid.redraw();
  });
  attempt("domClickWeekText", function() {
    const targetText = String(week.weekCntNm || "");
    const elements = Array.from(document.querySelectorAll("div, span, td, a"));
    const el = elements.find(function(node) {
      const text = (node.innerText || node.textContent || "").trim();
      const rect = node.getBoundingClientRect();
      return text.indexOf(targetText) >= 0 && rect.width > 0 && rect.height > 0;
    });
    if (!el) throw new Error("visible week text not found");
    el.scrollIntoView({block: "center", inline: "center"});
    el.click();
  });
  attempt("domDoubleClickWeekText", function() {
    const targetText = String(week.weekCntNm || "");
    const elements = Array.from(document.querySelectorAll("div, span, td, a"));
    const el = elements.find(function(node) {
      const text = (node.innerText || node.textContent || "").trim();
      const rect = node.getBoundingClientRect();
      return text.indexOf(targetText) >= 0 && rect.width > 0 && rect.height > 0;
    });
    if (!el) throw new Error("visible week text not found");
    el.scrollIntoView({block: "center", inline: "center"});
    el.dispatchEvent(new MouseEvent("dblclick", {bubbles: true, cancelable: true, view: window}));
  });

  let selected = null;
  try {
    selected = {
      index: typeof grid.getSelectedRowIndex === "function" ? grid.getSelectedRowIndex() : null,
      indices: typeof grid.getSelectedRowIndices === "function" ? grid.getSelectedRowIndices() : null
    };
  } catch(e) {
    selected = {error: e.message};
  }

  return {ok: true, rowIndex: rowIndex, week: week, attempts: attempts, selected: selected};
})(arguments[0], arguments[1]);
"""


JS_COUNTS = r"""
return (function(appId) {
  const platform = window.cpr && cpr.core && cpr.core.Platform && cpr.core.Platform.INSTANCE;
  const app = platform.getAllRunningAppInstances().find(function(ai) {
    return ai && ai.app && ai.app.id === appId;
  });
  if (!app) return {ok: false, error: "app not open"};
  function count(id) {
    const ds = app.lookup(id);
    return ds && ds.getRowCount ? ds.getRowCount() : null;
  }
  return {
    ok: true,
    dsWeekList: count("dsWeekList"),
    dsWeekByClsByTi: count("dsWeekByClsByTi"),
    dsHcntList: count("dsHcntList")
  };
})(arguments[0]);
"""


def attach_chrome(port: int):
    os.environ["no_proxy"] = "127.0.0.1,localhost"
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2):
            pass
    except (OSError, urllib.error.URLError) as exc:
        raise RuntimeError(f"CDP endpoint is not responding: {exc}") from exc

    opts = Options()
    opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
    return webdriver.Chrome(options=opts)


def switch_to_neis_cpr_window(driver) -> bool:
    for handle in driver.window_handles:
        driver.switch_to.window(handle)
        driver.switch_to.default_content()
        try:
            if driver.execute_script("return typeof cpr !== 'undefined';") and "vpn" not in driver.current_url.lower():
                return True
        except Exception:
            pass
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Select target week in timetable grid")
    parser.add_argument("--port", type=int, default=9222)
    parser.add_argument("--target-date", default="20260925")
    parser.add_argument("--wait", type=float, default=4.0)
    parser.add_argument("--real-click", action="store_true", help="Also perform a Selenium mouse click on the visible selected row")
    args = parser.parse_args()

    try:
        driver = attach_chrome(args.port)
    except Exception as exc:
        print(f"[connect:error] {exc}")
        return 3

    if not switch_to_neis_cpr_window(driver):
        print("[connect:error] cpr Platform이 있는 나이스 화면을 찾지 못했습니다.")
        return 4

    print(f"[connect] {driver.title}")
    before = driver.execute_script(JS_COUNTS, APP_ID)
    print("[before]", json.dumps(before, ensure_ascii=False))
    result = driver.execute_script(JS_SELECT_WEEK, APP_ID, args.target_date)
    print("[select]", json.dumps(result, ensure_ascii=False))
    if args.real_click and result.get("week"):
        # eXBuilder grid row selection can update styling without firing the app's mouse handler.
        # A browser-level click on the rendered row is closer to a user's click.
        row_rect = driver.execute_script(
            """
            const targetText = arguments[0];
            const elements = Array.from(document.querySelectorAll("div, span, td, a"));
            const matches = elements.filter(function(node) {
              const text = (node.innerText || node.textContent || "").trim();
              const rect = node.getBoundingClientRect();
              return text.indexOf(targetText) >= 0 && rect.width > 0 && rect.height > 0;
            });
            matches.sort(function(a, b) {
              const ar = a.getBoundingClientRect();
              const br = b.getBoundingClientRect();
              const aRow = a.classList && a.classList.contains("cl-grid-row") ? 0 : 1;
              const bRow = b.classList && b.classList.contains("cl-grid-row") ? 0 : 1;
              if (aRow !== bRow) return aRow - bRow;
              return (ar.width * ar.height) - (br.width * br.height);
            });
            const el = matches[0];
            if (!el) return null;
            const row = el.closest(".cl-grid-row") || el;
            const rect = row.getBoundingClientRect();
            return {x: rect.x, y: rect.y, w: rect.width, h: rect.height, text: row.innerText || row.textContent || ""};
            """,
            result["week"]["weekCntNm"],
        )
        print("[real-click:rect]", json.dumps(row_rect, ensure_ascii=False))
        if row_rect:
            x = int(row_rect["x"] + min(100, row_rect["w"] / 2))
            y = int(row_rect["y"] + row_rect["h"] / 2)
            ActionChains(driver).move_by_offset(x, y).click().move_by_offset(-x, -y).perform()
            print("[real-click]", json.dumps({"ok": True, "x": x, "y": y}, ensure_ascii=False))
    time.sleep(args.wait)
    after = driver.execute_script(JS_COUNTS, APP_ID)
    print("[after]", json.dumps(after, ensure_ascii=False))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
