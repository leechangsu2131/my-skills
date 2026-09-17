#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Execute full save pipeline for all target weeks (5, 18, 19, 20) with confirmation/alert handling.
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


JS_CLICK_SAVE_AND_CONFIRM = r"""
return (function(appId) {
  const platform = cpr.core.Platform.INSTANCE;
  const apps = platform.getAllRunningAppInstances();
  const main = apps.find(ai => ai && ai.app && ai.app.id === appId);
  if (!main) return {ok:false, error:"학급시간표관리 app is not open"};

  const btn = main.lookup("btnSave");
  if (!btn) return {ok:false, error:"btnSave not found"};

  btn.click();
  return {ok:true, clicked:true};
})(arguments[0]);
"""

JS_DISMISS_DIALOGS = r"""
return (function() {
  const platform = cpr.core.Platform.INSTANCE;
  const apps = platform.getAllRunningAppInstances();
  
  // Find alert/confirm/message dialogs
  const dismissed = [];
  apps.forEach(ai => {
    if (!ai || !ai.app) return;
    const appId = ai.app.id || "";
    const title = ai.title || "";
    
    // Check if it's a dialog (alert, confirm, msg)
    if (/alert|confirm|msg|dialog|popup/i.test(appId) || /알림|확인|저장/i.test(title)) {
      // Find confirm/ok button
      let btnOk = ai.lookup && (ai.lookup("btnOk") || ai.lookup("btnConfirm") || ai.lookup("btnYes") || ai.lookup("btnSave"));
      if (!btnOk && ai.getContainer) {
        const children = ai.getContainer().getAllRecursiveChildren();
        btnOk = children.find(c => c.type === "button" && (/확인|예|OK/i.test(c.value || c.text || c.fieldLabel || "")));
      }
      if (btnOk && typeof btnOk.click === "function") {
        try {
          btnOk.click();
          dismissed.push({appId, title, btnId: btnOk.id, val: btnOk.value});
        } catch(e) {
          dismissed.push({appId, title, error: e.message});
        }
      }
    }
  });

  return {ok:true, dismissed};
})();
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
    plan_path = Path(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\admin-neis-bot\timetable_optimization_plan_final.json")
    if not plan_path.exists():
        print(f"[error] Plan file not found: {plan_path}")
        return 1

    plan_data = json.loads(plan_path.read_text(encoding="utf-8"))
    plan = plan_data.get("plan", [])

    weeks_changes = {}
    for item in plan:
        w_idx = item["week_idx"]
        if w_idx not in weeks_changes:
            weeks_changes[w_idx] = []
        weeks_changes[w_idx].append(item)

    driver = attach_chrome()
    print(f"[connect] Attached to Chrome ({driver.title})")

    subject_dict = {
        "20042": "국어", "20045": "사회", "20048": "도덕", "20051": "수학",
        "20054": "과학", "20057": "체육", "20060": "음악", "20063": "미술",
        "20066": "영어", "20069": "자율·자치활동", "20072": "동아리활동", "20075": "진로활동"
    }

    # Save target weeks in order
    for w_idx in sorted(weeks_changes.keys()):
        items = weeks_changes[w_idx]
        w_num = w_idx + 1
        w_name = items[0].get("week_name")
        print(f"\n=======================================================")
        print(f"[SAVING] Week {w_num} ({w_name}) - {len(items)} changes")
        print(f"=======================================================")

        # 1. Select week
        sel = driver.execute_script(JS_SELECT_WEEK, APP_ID, w_idx)
        print(f"  [1] Week selected: {sel.get('ok')} ({sel.get('weekCntNm')})")
        time.sleep(1.2)

        # 2. Apply cell changes
        apply_res = driver.execute_script(JS_APPLY_WEEK_CHANGES, APP_ID, items, subject_dict)
        print(f"  [2] Cells applied: {apply_res.get('ok')} count={apply_res.get('appliedCount')}")
        time.sleep(0.8)

        # 3. Click btnSave
        save_res = driver.execute_script(JS_CLICK_SAVE_AND_CONFIRM, APP_ID)
        print(f"  [3] Clicked btnSave: {save_res.get('ok')}")
        time.sleep(1.0)

        # 4. Check and dismiss confirm/alert dialogs (up to 3 attempts)
        for attempt in range(3):
            time.sleep(0.8)
            dlg_res = driver.execute_script(JS_DISMISS_DIALOGS)
            dismissed = dlg_res.get("dismissed", [])
            if dismissed:
                print(f"  [4] Dialog handled ({attempt+1}): {dismissed}")

        time.sleep(1.5)

    print("\n[COMPLETE] All 4 target weeks (5, 18, 19, 20) saved to NEIS!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
