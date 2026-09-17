#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Collect all loaded weekly timetables for the open 학급시간표관리 screen.

This script is read-only. It sets the timetable condition, clicks each visible
week row, waits for the right-side timetable to load, and writes a JSON snapshot
that can be used to plan minimum timetable edits for zero subject deviation.
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
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options


APP_ID = "edu/sw/els/edc/tm/els_edctm00_m00"

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


JS_SET_CONDITION = r"""
return (function(appId, sem, grade, cls) {
  const platform = cpr.core.Platform.INSTANCE;
  const apps = platform.getAllRunningAppInstances();
  const main = apps.find(ai => ai && ai.app && ai.app.id === appId);
  if (!main) return {ok:false, error:"학급시간표관리 app is not open"};

  function setAuth(label, value) {
    const udc = apps.find(function(ai) {
      if (!ai || !ai.app || ai.app.id !== "udc/sw/swc/udcSwcAuth") return false;
      const cmb = ai.lookup && ai.lookup("cmbUdcAuth");
      return cmb && cmb.fieldLabel === label;
    });
    if (!udc || !value) return null;
    const cmb = udc.lookup("cmbUdcAuth");
    const before = String(cmb.value || "");
    cmb.value = value;
    try {
      cmb.dispatchEvent(new cpr.events.CValueChangeEvent("value-change", before, value));
    } catch(e) {
      try { cmb.dispatchEvent(new cpr.events.CUIEvent("value-change")); } catch(_) {}
    }
    try { cmb.redraw(); } catch(e) {}
    return {label, before, after:String(cmb.value || "")};
  }

  const changes = [setAuth("학기", sem), setAuth("학년", grade), setAuth("반", cls)].filter(Boolean);
  const btn = main.lookup("btnSearch");
  if (!btn || typeof btn.click !== "function") return {ok:false, error:"btnSearch not found", changes};
  btn.click();
  return {ok:true, changes};
})(arguments[0], arguments[1], arguments[2], arguments[3]);
"""


JS_SNAPSHOT = r"""
return (function(appId) {
  const platform = cpr.core.Platform.INSTANCE;
  const app = platform.getAllRunningAppInstances().find(ai => ai && ai.app && ai.app.id === appId);
  if (!app) return {ok:false, error:"학급시간표관리 app is not open"};

  function columnsOf(ds) {
    try { if (ds.getColumnNames) return ds.getColumnNames(); } catch(e) {}
    return [];
  }
  function rowsOf(id) {
    const ds = app.lookup(id);
    if (!ds || !ds.getRowCount) return [];
    const cols = columnsOf(ds);
    const rows = [];
    for (let r = 0; r < ds.getRowCount(); r++) {
      const row = {__rowIndex:r};
      cols.forEach(col => {
        try { row[col] = ds.getValue(r, col); } catch(e) {}
      });
      rows.push(row);
    }
    return rows;
  }
  return {
    ok:true,
    weekList: rowsOf("dsWeekList"),
    hcntList: rowsOf("dsHcntList"),
    subjectList: rowsOf("dsAyrSemGrdByEtbSbjt")
  };
})(arguments[0]);
"""


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
      return {ok:true, rowIndex, weekCntNm, weekBgngYmd, method:"cell-click-handler"};
    } catch(err) {
      return {ok:false, error:err.message, rowIndex, weekCntNm};
    }
  }

  return {ok:false, error:"cell-click handler not found", rowIndex, weekCntNm};
})(arguments[0], arguments[1]);
"""



JS_TIMETABLE = r"""
return (function(appId) {
  const app = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(ai => ai && ai.app && ai.app.id === appId);
  if (!app) return {ok:false, error:"학급시간표관리 app is not open"};
  const ds = app.lookup("dsWeekByClsByTi");
  if (!ds || !ds.getRowCount) return {ok:false, error:"dsWeekByClsByTi missing"};
  const cols = ds.getColumnNames ? ds.getColumnNames() : [];
  const rows = [];
  for (let r = 0; r < ds.getRowCount(); r++) {
    const row = {__rowIndex:r};
    cols.forEach(col => {
      try { row[col] = ds.getValue(r, col); } catch(e) {}
    });
    rows.push(row);
  }
  return {ok:true, rowCount:ds.getRowCount(), rows};
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


def write_json(prefix: str, data: dict) -> Path:
    path = Path(__file__).parent / f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def loaded_week_matches(timetable: dict, week: dict) -> bool:
    rows = timetable.get("rows") or []
    if not rows:
        return False
    return str(rows[0].get("monYmd") or "") == str(week.get("weekBgngYmd") or "")


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect 2학기 weekly timetable snapshots")
    parser.add_argument("--port", type=int, default=9222)
    parser.add_argument("--sem", default="2")
    parser.add_argument("--grade", default="3")
    parser.add_argument("--class-code", default="02")
    parser.add_argument("--wait-search", type=float, default=7.0)
    parser.add_argument("--wait-week", type=float, default=2.0)
    parser.add_argument("--start-week", type=int, default=1, help="1-based week index to start collecting")
    parser.add_argument("--end-week", type=int, default=0, help="1-based week index to stop collecting; 0 means all")
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
    result = driver.execute_script(JS_SET_CONDITION, APP_ID, args.sem, args.grade, args.class_code)
    print("[condition]", json.dumps(result, ensure_ascii=False))
    if not result.get("ok"):
        return 1
    time.sleep(args.wait_search)

    base = driver.execute_script(JS_SNAPSHOT, APP_ID)
    if not base.get("ok"):
        print("[snapshot:error]", json.dumps(base, ensure_ascii=False))
        return 1

    weeks = base.get("weekList") or []
    start = max(args.start_week, 1)
    end = args.end_week if args.end_week else len(weeks)
    selected_weeks = weeks[start - 1:end]
    collected = []
    for offset, week in enumerate(selected_weeks, start=start):
        idx = week.get("__rowIndex")
        print(f"[week] {offset}/{len(weeks)} {week.get('weekCntNm')}")
        select = driver.execute_script(JS_SELECT_WEEK, APP_ID, idx)
        time.sleep(args.wait_week)
        timetable = driver.execute_script(JS_TIMETABLE, APP_ID)
        if not loaded_week_matches(timetable, week):
            time.sleep(args.wait_week + 1)
            timetable = driver.execute_script(JS_TIMETABLE, APP_ID)
        ok = loaded_week_matches(timetable, week)
        print(f"  loaded={ok} rows={timetable.get('rowCount')} mon={((timetable.get('rows') or [{}])[0]).get('monYmd')}")
        collected.append({"week": week, "select": select, "loaded": ok, "timetable": timetable})


    output = {
        "condition": {"sem": args.sem, "grade": args.grade, "classCode": args.class_code},
        "base": base,
        "weeks": collected,
    }
    path = write_json("semester_timetable_collection", output)
    print(f"[json] {path}")
    failed = [w for w in collected if not w.get("loaded")]
    print(f"[summary] weeks={len(collected)} failed={len(failed)}")
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())
