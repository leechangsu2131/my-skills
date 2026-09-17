#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Set 학급시간표관리 search conditions and click 조회.

This changes only screen search controls. It does not edit timetable cells and
does not click any save/apply control.
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
from selenium.webdriver.chrome.options import Options


APP_ID = "edu/sw/els/edc/tm/els_edctm00_m00"

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


JS_SET_AND_SEARCH = r"""
return (function(appId, sem, grade, cls) {
  const platform = window.cpr && cpr.core && cpr.core.Platform && cpr.core.Platform.INSTANCE;
  if (!platform) return {ok: false, error: "cpr Platform is not available"};

  const apps = platform.getAllRunningAppInstances();
  const main = apps.find(function(ai) { return ai && ai.app && ai.app.id === appId; });
  if (!main) return {ok: false, error: "학급시간표관리 app is not open"};

  function dispatchValueChange(control, before, after) {
    try {
      if (cpr.events && cpr.events.CValueChangeEvent) {
        control.dispatchEvent(new cpr.events.CValueChangeEvent("value-change", before, after));
        return "CValueChangeEvent";
      }
    } catch(e) {}
    try {
      control.dispatchEvent(new cpr.events.CUIEvent("value-change"));
      return "CUIEvent:value-change";
    } catch(e) {}
    return "";
  }

  function setAuthByLabel(label, value) {
    if (!value) return null;
    const udc = apps.find(function(ai) {
      if (!ai || !ai.app || ai.app.id !== "udc/sw/swc/udcSwcAuth") return false;
      const cmb = ai.lookup && ai.lookup("cmbUdcAuth");
      return cmb && cmb.fieldLabel === label;
    });
    if (!udc) return {label: label, ok: false, error: "udc not found"};
    const cmb = udc.lookup("cmbUdcAuth");
    const before = String(cmb.value || "");
    cmb.value = value;
    const event = dispatchValueChange(cmb, before, value);
    try { cmb.redraw(); } catch(e) {}
    return {label: label, ok: true, before: before, after: String(cmb.value || ""), event: event};
  }

  const changed = [
    setAuthByLabel("학기", sem),
    setAuthByLabel("학년", grade),
    setAuthByLabel("반", cls)
  ].filter(Boolean);

  const btn = main.lookup("btnSearch");
  if (!btn || typeof btn.click !== "function") return {ok: false, changed: changed, error: "btnSearch not found"};
  btn.click();

  return {ok: true, changed: changed, clickedSearch: true};
})(arguments[0], arguments[1], arguments[2], arguments[3]);
"""


JS_COUNTS = r"""
return (function(appId) {
  const platform = window.cpr && cpr.core && cpr.core.Platform && cpr.core.Platform.INSTANCE;
  const apps = platform.getAllRunningAppInstances();
  const main = apps.find(function(ai) { return ai && ai.app && ai.app.id === appId; });
  if (!main) return {ok: false, error: "app not open"};

  function count(id) {
    const ds = main.lookup(id);
    return ds && ds.getRowCount ? ds.getRowCount() : null;
  }

  const auth = apps.filter(function(ai) {
    return ai && ai.app && ai.app.id === "udc/sw/swc/udcSwcAuth";
  }).map(function(ai) {
    const cmb = ai.lookup("cmbUdcAuth");
    return {
      label: cmb && cmb.fieldLabel || "",
      value: cmb && String(cmb.value || ""),
      text: cmb && String(cmb.text || "")
    };
  });

  return {
    ok: true,
    auth: auth,
    dsWeekList: count("dsWeekList"),
    dsWeekByClsByTi: count("dsWeekByClsByTi"),
    dsAyrSemGrdByEtbSbjt: count("dsAyrSemGrdByEtbSbjt"),
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
    parser = argparse.ArgumentParser(description="Set timetable search condition and click search")
    parser.add_argument("--port", type=int, default=9222)
    parser.add_argument("--sem", default="")
    parser.add_argument("--grade", default="")
    parser.add_argument("--class-code", default="")
    parser.add_argument("--wait", type=float, default=6.0)
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
    result = driver.execute_script(JS_SET_AND_SEARCH, APP_ID, args.sem, args.grade, args.class_code)
    print("[set/search]", json.dumps(result, ensure_ascii=False))
    time.sleep(args.wait)
    after = driver.execute_script(JS_COUNTS, APP_ID)
    print("[after]", json.dumps(after, ensure_ascii=False))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
