#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Click one eXBuilder6 control and dump running app structure.

This helper is for read-only exploration of NEIS screens. It blocks common
mutating controls by default, then records app/control/dataset state after a
safe navigation or popup-opening click.
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
from selenium.webdriver.chrome.options import Options


BLOCKED_CONTROL_IDS = {
    "btnSave",
    "btnDelete",
    "btnDel",
    "btnInsert",
    "btnAdd",
    "btnApply",
    "btnAply",
    "btnBndeAply",
    "btnSubmit",
    "btnAprv",
}

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


JS_CLICK_CONTROL = r"""
return (function(appId, controlId, labelContains) {
  const platform = window.cpr && cpr.core && cpr.core.Platform && cpr.core.Platform.INSTANCE;
  if (!platform) return {ok: false, error: "cpr Platform is not available"};

  const apps = platform.getAllRunningAppInstances();
  let targetApp = null;
  if (appId) {
    targetApp = apps.find(function(ai) { return ai && ai.app && ai.app.id === appId; });
  }
  if (!targetApp) {
    targetApp = apps.find(function(ai) {
      try { return ai && ai.lookup && ai.lookup(controlId); } catch(e) { return false; }
    });
  }
  if (!targetApp) return {ok: false, error: "target app not found"};

  const control = targetApp.lookup ? targetApp.lookup(controlId) : null;
  if (!control) return {ok: false, error: "control not found", appId: targetApp.app && targetApp.app.id};

  const value = control.value === undefined || control.value === null ? "" : String(control.value);
  const fieldLabel = control.fieldLabel === undefined || control.fieldLabel === null ? "" : String(control.fieldLabel);
  if (labelContains && (value + " " + fieldLabel).indexOf(labelContains) < 0) {
    return {ok: false, error: "label guard failed", value: value, fieldLabel: fieldLabel};
  }

  if (typeof control.click !== "function") {
    return {ok: false, error: "control has no click()", type: control.type || ""};
  }

  control.click();
  return {
    ok: true,
    appId: targetApp.app && targetApp.app.id,
    controlId: controlId,
    type: control.type || "",
    value: value,
    fieldLabel: fieldLabel
  };
})(arguments[0], arguments[1], arguments[2]);
"""


JS_DUMP_APPS = r"""
return (function(sampleRows) {
  const platform = window.cpr && cpr.core && cpr.core.Platform && cpr.core.Platform.INSTANCE;
  if (!platform) return {error: "cpr Platform is not available"};

  function columnsOf(ds) {
    try { if (ds.getColumnNames) return ds.getColumnNames(); } catch(e) {}
    const cols = [];
    try {
      if (ds.getColumnCount && ds.getColumn) {
        for (let i = 0; i < ds.getColumnCount(); i++) {
          const col = ds.getColumn(i);
          cols.push(col && (col.columnName || col.name || String(col)));
        }
      }
    } catch(e) {}
    return cols.filter(Boolean);
  }

  const apps = platform.getAllRunningAppInstances().map(function(ai, idx) {
    const controls = [];
    const datasets = [];
    try {
      const children = ai.getContainer && ai.getContainer().getAllRecursiveChildren
        ? ai.getContainer().getAllRecursiveChildren()
        : [];
      children.forEach(function(c) {
        controls.push({
          id: c.id || "",
          type: c.type || (c.constructor && c.constructor.name) || "",
          fieldLabel: c.fieldLabel || "",
          value: typeof c.value !== "undefined" ? String(c.value).slice(0, 120) : "",
          text: c.text ? String(c.text).slice(0, 120) : ""
        });
      });
    } catch(e) {
      controls.push({error: e.message});
    }

    try {
      const dataControls = ai.getAllDataControls ? ai.getAllDataControls() : [];
      dataControls.forEach(function(ds) {
        if (!ds || ds.type !== "dataset") return;
        const cols = columnsOf(ds);
        const rowCount = ds.getRowCount ? ds.getRowCount() : 0;
        const rows = [];
        for (let r = 0; r < Math.min(rowCount, sampleRows); r++) {
          const row = {};
          cols.slice(0, 40).forEach(function(col) {
            try { row[col] = ds.getValue(r, col); } catch(e) {}
          });
          rows.push(row);
        }
        datasets.push({id: ds.id || "", type: ds.type || "", rowCount: rowCount, columns: cols, sampleRows: rows});
      });
    } catch(e) {
      datasets.push({error: e.message});
    }

    return {
      idx: idx,
      appId: ai.app && ai.app.id,
      title: ai.title || "",
      controlsCount: controls.length,
      controls: controls,
      datasets: datasets
    };
  });

  return {ok: true, apps: apps};
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Click a NEIS eXBuilder control and dump app state")
    parser.add_argument("--port", type=int, default=9222)
    parser.add_argument("--app-id")
    parser.add_argument("--control-id", required=True)
    parser.add_argument("--label-contains", help="Guard: value or fieldLabel must contain this text")
    parser.add_argument("--wait", type=float, default=3.0)
    parser.add_argument("--sample-rows", type=int, default=5)
    parser.add_argument("--dump-prefix", default="control_click_active_apps")
    parser.add_argument("--allow-dangerous", action="store_true")
    args = parser.parse_args()

    if args.control_id in BLOCKED_CONTROL_IDS and not args.allow_dangerous:
        print(f"[blocked] {args.control_id} is a commonly mutating control. Use --allow-dangerous only after explicit approval.")
        return 2

    try:
        driver = attach_chrome(args.port)
    except Exception as exc:
        print(f"[connect:error] {exc}")
        return 3

    if not switch_to_neis_cpr_window(driver):
        print("[connect:error] cpr Platform이 있는 나이스 화면을 찾지 못했습니다.")
        return 4

    print(f"[connect] {driver.title}")
    result = driver.execute_script(JS_CLICK_CONTROL, args.app_id or "", args.control_id, args.label_contains or "")
    print("[click]", json.dumps(result, ensure_ascii=False))
    time.sleep(args.wait)

    dump = driver.execute_script(JS_DUMP_APPS, args.sample_rows)
    path = write_json(args.dump_prefix, {"click": result, "dump": dump})
    print(f"[apps:json] {path}")

    for app in dump.get("apps", []):
      datasets = ", ".join(f"{ds.get('id')}({ds.get('rowCount')})" for ds in app.get("datasets", []) if ds.get("id"))
      print(f"- {app.get('appId')} | controls={app.get('controlsCount')} | datasets={datasets}")

    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
