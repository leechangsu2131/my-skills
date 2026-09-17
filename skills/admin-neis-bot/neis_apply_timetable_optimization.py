#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Apply zero-deviation timetable optimization plan to open NEIS 학급시간표관리 screen.

Safe execution:
- Default is dry-run mode (plans and previews).
- --apply modifies the in-memory dataset/grid for target weeks (5, 18, 19, 20).
- --save actually clicks btnSave only when explicitly requested.
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
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

APP_ID = "edu/sw/els/edc/tm/els_edctm00_m00"

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


JS_SELECT_WEEK = r"""
return (function(appId, rowIndex) {
  const platform = cpr.core.Platform.INSTANCE;
  const app = platform.getAllRunningAppInstances().find(ai => ai && ai.app && ai.app.id === appId);
  if (!app) return {ok:false, error:"학급시간표관리 app is not open"};
  const dsWeek = app.lookup("dsWeekList");
  const grid = app.lookup("grdWeek");
  if (!dsWeek || !grid) return {ok:false, error:"week controls missing"};
  const weekCntNm = dsWeek.getValue(rowIndex, "weekCntNm");
  const weekBgngYmd = dsWeek.getValue(rowIndex, "weekBgngYmd");

  try { grid.selectRows([rowIndex]); } catch(e) {}
  try { grid.focusCell(rowIndex, 0); } catch(e) {}

  const listeners = grid._eventListenerList && grid._eventListenerList["cell-click"];
  const handler = listeners && listeners[0];
  if (handler) {
    const fakeEvent = {
      control: grid,
      rowIndex: rowIndex,
      cellIndex: 0,
      row: grid.getRow ? grid.getRow(rowIndex) : null,
      target: grid
    };
    try {
      handler.call(grid, fakeEvent, rowIndex);
      return {ok:true, rowIndex, weekCntNm, weekBgngYmd};
    } catch(err) {
      return {ok:false, error:err.message, rowIndex, weekCntNm};
    }
  }

  return {ok:false, error:"cell-click handler not found", rowIndex, weekCntNm};
})(arguments[0], arguments[1]);
"""


JS_APPLY_WEEK_CHANGES = r"""
return (function(appId, changesForWeek, subjectDict) {
  const app = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(ai => ai && ai.app && ai.app.id === appId);
  if (!app) return {ok:false, error:"학급시간표관리 app is not open"};
  const ds = app.lookup("dsWeekByClsByTi");
  if (!ds) return {ok:false, error:"dsWeekByClsByTi missing"};
  const grid = app.lookup("grdTimetable") || app.lookup("grdWeekByClsByTi");

  const results = [];
  changesForWeek.forEach(function(item) {
    const pir = item.pir; // 1..8
    const rowIndex = pir - 1;
    const day = item.day; // 'mon', 'tue', etc.
    const toSbjt = item.to_sbjt || "";
    const toTcr = item.to_tcr || "";
    const toName = subjectDict[toSbjt] || item.to_name || "";

    const infoCol = day + "Info";
    const otptCol = day + "Otpt";

    const beforeInfo = ds.getValue(rowIndex, infoCol) || "";
    const beforeOtpt = ds.getValue(rowIndex, otptCol) || "";

    let newInfo = "";
    let newOtpt = "";

    if (toSbjt) {
      newInfo = "01|" + toSbjt + "|" + toTcr + "|4||";
      newOtpt = "<div></div>" + toName + "<br/>(" + (toTcr === "lee2131" ? "이창수" : toTcr) + "(" + toTcr + "))";
    } else {
      newInfo = "";
      newOtpt = "";
    }

    try {
      ds.setValue(rowIndex, infoCol, newInfo);
      ds.setValue(rowIndex, otptCol, newOtpt);
      results.push({
        day: day,
        pir: pir,
        beforeInfo: beforeInfo,
        afterInfo: newInfo,
        beforeOtpt: beforeOtpt,
        afterOtpt: newOtpt
      });
    } catch(err) {
      results.push({day: day, pir: pir, error: err.message});
    }
  });

  try { if (grid && grid.redraw) grid.redraw(); } catch(_) {}
  try { if (ds && ds.redraw) ds.redraw(); } catch(_) {}

  return {ok:true, appliedCount:results.length, results:results};
})(arguments[0], arguments[1], arguments[2]);
"""


JS_CLICK_SAVE = r"""
return (function(appId) {
  const app = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(ai => ai && ai.app && ai.app.id === appId);
  if (!app) return {ok:false, error:"학급시간표관리 app is not open"};
  const btn = app.lookup("btnSave");
  if (!btn) return {ok:false, error:"btnSave not found"};
  btn.click();
  return {ok:true, clicked:true};
})(arguments[0]);
"""


def attach_chrome(port: int = 9222):
    os.environ["no_proxy"] = "127.0.0.1,localhost"
    opts = Options()
    opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
    driver = webdriver.Chrome(options=opts)
    for handle in driver.window_handles:
        driver.switch_to.window(handle)
        driver.switch_to.default_content()
        try:
            if driver.execute_script("return typeof cpr !== 'undefined';") and "vpn" not in driver.current_url.lower():
                return driver
        except Exception:
            pass
    raise RuntimeError("NEIS cpr window not found")


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply timetable optimization plan")
    parser.add_argument("--plan-file", default="timetable_optimization_plan_final.json")
    parser.add_argument("--apply", action="store_true", help="Apply draft changes to NEIS in-memory grid")
    parser.add_argument("--save", action="store_true", help="Click btnSave after applying each week")
    args = parser.parse_args()

    plan_path = Path(__file__).parent / args.plan_file
    if not plan_path.exists():
        print(f"[error] Plan file not found: {plan_path}")
        return 1

    plan_data = json.loads(plan_path.read_text(encoding="utf-8"))
    plan = plan_data.get("plan", [])
    print(f"[plan] Loaded {len(plan)} cell changes from {plan_path.name}")

    # Group changes by week_idx
    weeks_changes = {}
    for item in plan:
        w_idx = item["week_idx"]
        if w_idx not in weeks_changes:
            weeks_changes[w_idx] = []
        weeks_changes[w_idx].append(item)

    print(f"[plan] Target weeks: {[w+1 for w in sorted(weeks_changes.keys())]}")

    if not args.apply:
        print("\n[DRY-RUN MODE] Preview of changes by week:")
        for w_idx in sorted(weeks_changes.keys()):
            items = weeks_changes[w_idx]
            w_name = items[0].get("week_name")
            print(f"\n--- Week {w_idx+1} ({w_name}) : {len(items)} changes ---")
            for it in items:
                print(f"  {it['day']:3s} {it['pir']}교시: {it['from_name']} -> {it['to_name']} ({it['reason']})")
        print("\nTo apply these changes into NEIS screen, run with --apply")
        return 0

    driver = attach_chrome()
    print(f"[connect] Attached to Chrome ({driver.title})")

    subject_dict = {
        "20042": "국어", "20045": "사회", "20048": "도덕", "20051": "수학",
        "20054": "과학", "20057": "체육", "20060": "음악", "20063": "미술",
        "20066": "영어", "20069": "자율·자치활동", "20072": "동아리활동", "20075": "진로활동"
    }

    for w_idx in sorted(weeks_changes.keys()):
        items = weeks_changes[w_idx]
        w_num = w_idx + 1
        print(f"\n[applying] Week {w_num} ({items[0].get('week_name')})...")
        
        # 1. Select week
        sel = driver.execute_script(JS_SELECT_WEEK, APP_ID, w_idx)
        print(f"  Selected: {sel.get('ok')} {sel.get('weekCntNm')}")
        time.sleep(1.2)

        # 2. Apply cell changes
        res = driver.execute_script(JS_APPLY_WEEK_CHANGES, APP_ID, items, subject_dict)
        print(f"  Applied: {res.get('ok')} count={res.get('appliedCount')}")
        time.sleep(0.5)

        # 3. Save if requested
        if args.save:
            save_res = driver.execute_script(JS_CLICK_SAVE, APP_ID)
            print(f"  Saved: {save_res.get('ok')}")
            time.sleep(1.5)

    print("\n[DONE] All week changes successfully applied!")
    if not args.save:
        print("[NOTE] Changes are currently loaded in the NEIS screen/grid. Please review and click '저장' or run with --save.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
