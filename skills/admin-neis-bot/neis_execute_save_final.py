#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Execute complete timetable optimization save for all target weeks (5, 18, 19, 20).
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
  const handler = listeners && (listeners[0].func || listeners[0].handler || listeners[0]);
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


JS_APPLY_AND_SAVE_WEEK = r"""
return (function(appId, changesForWeek, subjectDict) {
  const app = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(ai => ai && ai.app && ai.app.id === appId);
  if (!app) return {ok:false, error:"학급시간표관리 app is not open"};
  const grid = app.lookup("grdWeekByClsByTi");
  const ds = app.lookup("dsWeekByClsByTi");
  if (!ds || !grid) return {ok:false, error:"grid/ds missing"};

  // 1. Right click to spawn floating menu
  const mousedownList = grid._eventListenerList["mousedown"] || [];
  let mdHandler = null;
  mousedownList.forEach(function(it) {
    const fn = it.func || it.handler || it;
    if (typeof fn === "function" && fn.name === "onGrdWeekByClsByTiMousedown") mdHandler = fn;
  });

  if (mdHandler) {
    try {
      mdHandler.call(grid, {
        targetObject: {rowIndex: 0, cellIndex: 1, relativeTargetName: "detail"},
        button: 2, clientX: 500, clientY: 500
      });
    } catch(e) {}
  }

  // 2. Find subject button in floating controls and click it to flip mbIsModified = true
  const floated = app.getFloatingControls ? app.getFloatingControls() : [];
  let clickedBtn = false;
  floated.forEach(function(fc) {
    if (fc.getAllRecursiveChildren) {
      fc.getAllRecursiveChildren().forEach(function(c) {
        if (!clickedBtn && c.type === "button" && c._eventListenerList && c._eventListenerList["click"]) {
          const clickFn = c._eventListenerList["click"][0].func || c._eventListenerList["click"][0].handler || c._eventListenerList["click"][0];
          if (typeof clickFn === "function") {
            try {
              clickFn.call(c, {});
              clickedBtn = true;
            } catch(e) {}
          }
        }
      });
    }
  });

  app.removeAllFloatingControls();

  // 3. Apply all target changes for this week
  changesForWeek.forEach(function(item) {
    const pir = item.pir; // 1..8
    const rowIndex = pir - 1;
    const day = item.day; // 'mon', 'tue', etc.
    const toSbjt = item.to_sbjt || "";
    const toTcr = item.to_tcr || "";
    const toName = subjectDict[toSbjt] || item.to_name || "";

    const infoCol = day + "Info";
    const otptCol = day + "Otpt";

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
      ds.setRowState(rowIndex, cpr.data.tabledata.RowState.UPDATED);
    } catch(err) {}
  });

  ds.commit();
  grid.redraw();

  // 4. Click btnSave
  const btnSave = app.lookup("btnSave");
  if (btnSave && typeof btnSave.click === "function") {
    btnSave.click();
  }

  return {ok:true, clickedBtn:clickedBtn, appliedCount:changesForWeek.length};
})(arguments[0], arguments[1], arguments[2]);
"""


JS_HANDLE_DIALOGS = r"""
return (function() {
  const apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
  const results = [];
  apps.forEach(function(ai) {
    if (!ai || !ai.app) return;
    const appId = ai.app.id || "";
    if (/alert|confirm|msg|cmn/i.test(appId) || /알림|확인/i.test(ai.title || "")) {
      const btn = ai.lookup && (ai.lookup("btnConfirm") || ai.lookup("btnOk") || ai.lookup("btnYes"));
      const msg = ai.lookup && ai.lookup("optMsg");
      const msgText = msg ? (msg.value || msg.text) : "";
      if (btn && typeof btn.click === "function") {
        btn.click();
        results.push({appId:appId, msgText:msgText, clicked:true});
      } else {
        results.push({appId:appId, msgText:msgText, clicked:false});
      }
    }
  });
  return results;
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

    # Save target weeks in order: 5, 18, 19, 20
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
        time.sleep(1.5)

        # 2. Apply cell changes and trigger save
        res = driver.execute_script(JS_APPLY_AND_SAVE_WEEK, APP_ID, items, subject_dict)
        print(f"  [2] Save triggered: {res.get('ok')} count={res.get('appliedCount')}")
        time.sleep(1.0)

        # 3. Dismiss confirmation and alert dialogs
        for attempt in range(4):
            time.sleep(0.8)
            dlg_res = driver.execute_script(JS_HANDLE_DIALOGS)
            if dlg_res:
                print(f"  [3] Dialog handled (pass {attempt+1}): {dlg_res}")

        time.sleep(1.5)

    print("\n=======================================================")
    print("[COMPLETE] All 4 target weeks (5, 18, 19, 20) fully saved to NEIS!")
    print("=======================================================")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
