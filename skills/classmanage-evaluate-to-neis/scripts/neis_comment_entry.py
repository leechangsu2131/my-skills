#!/usr/bin/env python3
"""Diagnose or enter NEIS subject comments through the live CPR app."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REMOTE_PORT = 9222


def ensure_selenium():
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
    except ModuleNotFoundError as exc:
        raise SystemExit("Install selenium first: python -m pip install selenium") from exc
    return webdriver, Options


def attach(port: int = REMOTE_PORT):
    webdriver, Options = ensure_selenium()
    opts = Options()
    opts.add_experimental_option("debuggerAddress", f"localhost:{port}")
    driver = webdriver.Chrome(options=opts)
    print(f"[connect] {driver.title} {driver.current_url}")
    return driver


JS_DIAGNOSE = r"""
return (function() {
  function valueAt(ds, row, col) {
    try { return ds.getValue(row, col); } catch (e) { return null; }
  }
  function getCols(ds) {
    const cols = [];
    try {
      for (let i = 0; i < ds.getColumnCount(); i++) {
        const c = ds.getColumn(i);
        cols.push(c && (c.columnName || c.name || String(c)));
      }
    } catch (e) {}
    return cols.filter(Boolean);
  }
  const platform = window.cpr && cpr.core && cpr.core.Platform && cpr.core.Platform.INSTANCE;
  if (!platform) return {error: "window.cpr Platform is not available"};
  const apps = platform.getAllRunningAppInstances().map((ai, idx) => {
    const controls = [];
    const datasets = [];
    try {
      ai.getContainer().getAllRecursiveChildren().forEach(c => {
        controls.push({
          id: c.id || "",
          type: c.type || (c.constructor && c.constructor.name) || "",
          fieldLabel: c.fieldLabel || "",
          text: c.text || "",
          value: typeof c.value !== "undefined" ? c.value : null,
          itemCount: c.getItemCount ? c.getItemCount() : null,
          items: c.getItemCount ? Array.from({length: Math.min(c.getItemCount(), 12)}, (_, i) => {
            const item = c.getItem(i);
            return item ? {label: item.label, value: item.value} : null;
          }).filter(Boolean) : []
        });
      });
    } catch (e) {
      controls.push({error: String(e)});
    }
    try {
      const dataControls = ai.getAllDataControls ? ai.getAllDataControls() : [];
      dataControls.forEach(ds => {
        const cols = getCols(ds);
        datasets.push({
          id: ds.id || "",
          type: ds.type || (ds.constructor && ds.constructor.name) || "",
          rowCount: ds.getRowCount ? ds.getRowCount() : null,
          cols,
          sample: ds.getRowCount && ds.getRowCount() ? cols.slice(0, 20).reduce((o, col) => {
            o[col] = valueAt(ds, 0, col);
            return o;
          }, {}) : {}
        });
      });
    } catch (e) {
      datasets.push({error: String(e)});
    }
    return {idx, appId: ai.app && ai.app.id, title: ai.title || "", controls, datasets};
  });
  return {apps};
})();
"""


def diagnose(driver, dump: Path | None) -> dict[str, Any]:
    result = driver.execute_script(JS_DIAGNOSE)
    if dump:
        dump.parent.mkdir(parents=True, exist_ok=True)
        dump.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[diagnose] wrote {dump}")
    for app in result.get("apps", []):
        print(f"[app] {app.get('idx')} {app.get('appId')}")
        for ds in app.get("datasets", [])[:8]:
            print(f"  [ds] {ds.get('id')} rows={ds.get('rowCount')} cols={','.join(ds.get('cols', [])[:12])}")
        for ctl in app.get("controls", [])[:25]:
            label = ctl.get("fieldLabel") or ctl.get("text")
            if label or ctl.get("itemCount"):
                print(f"  [ctl] {ctl.get('id')} {ctl.get('type')} {label} items={ctl.get('itemCount')}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, help="Parsed comment revision JSON")
    parser.add_argument("--diagnose", action="store_true")
    parser.add_argument("--dump", type=Path)
    parser.add_argument("--port", type=int, default=REMOTE_PORT)
    args = parser.parse_args()

    if args.records:
        records = json.loads(args.records.read_text(encoding="utf-8"))
        print(f"records: {len(records)}")
    driver = attach(args.port)
    if args.diagnose:
        diagnose(driver, args.dump)
        return
    print("No write action implemented for this screen yet. Run --diagnose on the live page first.")


if __name__ == "__main__":
    main()
