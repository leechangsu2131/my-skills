#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NEIS semester-start menu explorer.

This is a read-only scout for the beginning-of-semester workflow.
It attaches to an already logged-in Chrome remote debugging session on
127.0.0.1:9222, searches the NEIS menu datasets for likely candidates,
optionally opens one menu, and dumps the active eXBuilder6 app structure.

Examples:
  python skills/admin-neis-bot/neis_semester_start_explorer.py
  python skills/admin-neis-bot/neis_semester_start_explorer.py --keywords "학급,담임,출석,시간표"
  python skills/admin-neis-bot/neis_semester_start_explorer.py --menu "학기말종합의견"
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


REMOTE_PORT = 9222
DEFAULT_KEYWORDS = [
    "학급",
    "담임",
    "학년",
    "반",
    "출석",
    "결석",
    "시간표",
    "교육과정",
    "학생부",
    "생활기록",
    "전입",
    "진급",
    "기초",
    "일괄",
]

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


JS_FIND_MENUS = r"""
return (function(keywords) {
  const platform = window.cpr && cpr.core && cpr.core.Platform && cpr.core.Platform.INSTANCE;
  if (!platform) return {error: "cpr Platform is not available"};

  const indexApp = platform.getAllRunningAppInstances().find(function(ai) {
    return ai && ai.app && ai.app.id === "app/com/main/Index";
  });
  if (!indexApp) return {error: "app/com/main/Index not found"};

  const datasetIds = ["dsAllMenu", "dsAllMenuNew", "dsAllMenuLocal"];
  const seen = {};
  const matches = [];

  function getValue(ds, row, names) {
    for (let i = 0; i < names.length; i++) {
      try {
        const value = ds.getValue(row, names[i]);
        if (value !== undefined && value !== null && String(value) !== "") return String(value);
      } catch (e) {}
    }
    return "";
  }

  datasetIds.forEach(function(dsId) {
    const ds = indexApp.lookup(dsId);
    if (!ds || !ds.getRowCount) return;
    const rowCount = ds.getRowCount();

    for (let r = 0; r < rowCount; r++) {
      const menuName = getValue(ds, r, ["MENU_NM", "menuNm"]);
      const path = getValue(ds, r, ["menuNmDepth", "pgePathNm", "DESC", "MENU_DESC"]);
      const haystack = [menuName, path].join(" ").toLowerCase();
      const hitKeywords = keywords.filter(function(k) {
        return haystack.indexOf(String(k).toLowerCase()) >= 0;
      });
      if (!hitKeywords.length) continue;

      const menuId = getValue(ds, r, ["MENU_ID", "menuId", "V_MENU_ID", "vMenuId"]);
      const pageId = getValue(ds, r, ["PGM_ID", "pgeId", "CALL_PAGE"]);
      const key = [menuName, menuId, pageId].join("|");
      if (seen[key]) continue;
      seen[key] = true;

      matches.push({
        dataset: dsId,
        row: r,
        menuName: menuName,
        path: path,
        menuId: menuId,
        upperMenuId: getValue(ds, r, ["UP_MENU_ID", "upMenuId", "V_UP_MENU_ID", "vUpMenuId"]),
        pageId: pageId,
        callPage: getValue(ds, r, ["CALL_PAGE", "CALL_PAGE_POP", "pgePathNm"]),
        level: getValue(ds, r, ["menuLvl"]),
        hits: hitKeywords
      });
    }
  });

  matches.sort(function(a, b) {
    if (b.hits.length !== a.hits.length) return b.hits.length - a.hits.length;
    return String(a.path + a.menuName).localeCompare(String(b.path + b.menuName));
  });

  return {ok: true, matches: matches};
})(arguments[0]);
"""


JS_SEARCH_MENU = r"""
return (function(menuName) {
  const platform = window.cpr && cpr.core && cpr.core.Platform && cpr.core.Platform.INSTANCE;
  if (!platform) return {ok: false, error: "cpr Platform is not available"};

  const indexApp = platform.getAllRunningAppInstances().find(function(ai) {
    return ai && ai.app && ai.app.id === "app/com/main/Index";
  });
  if (!indexApp) return {ok: false, error: "app/com/main/Index not found"};

  const searchInput = indexApp.lookup("siFindMenu");
  if (!searchInput) return {ok: false, error: "siFindMenu not found"};

  searchInput.value = menuName;
  try {
    searchInput.dispatchEvent(new cpr.events.CUIEvent("search"));
  } catch (e) {
    return {ok: false, error: "search event failed: " + e.message};
  }
  return {ok: true};
})(arguments[0]);
"""


JS_CLICK_MENU_TEXT = r"""
return (function(menuName) {
  const candidates = Array.from(document.querySelectorAll("a,span,div,td"));
  const exact = candidates.find(function(el) {
    const text = (el.innerText || el.textContent || "").trim();
    return text === menuName && el.offsetParent !== null;
  });
  if (exact) {
    exact.click();
    return {ok: true, method: "exact-dom-click", tagName: exact.tagName};
  }

  const partial = candidates.find(function(el) {
    const text = (el.innerText || el.textContent || "").trim();
    return text.indexOf(menuName) >= 0 && text.length <= menuName.length + 20 && el.offsetParent !== null;
  });
  if (partial) {
    partial.click();
    return {ok: true, method: "partial-dom-click", tagName: partial.tagName, text: partial.innerText};
  }

  return {ok: false, error: "visible menu text not found"};
})(arguments[0]);
"""


JS_DUMP_ACTIVE_APPS = r"""
return (function(sampleRows) {
  const platform = window.cpr && cpr.core && cpr.core.Platform && cpr.core.Platform.INSTANCE;
  if (!platform) return {error: "cpr Platform is not available"};

  function getColumns(ds) {
    try {
      if (ds.getColumnNames) return ds.getColumnNames();
    } catch (e) {}
    const cols = [];
    try {
      if (ds.getColumnCount && ds.getColumn) {
        for (let i = 0; i < ds.getColumnCount(); i++) {
          const col = ds.getColumn(i);
          cols.push(col && (col.columnName || col.name || String(col)));
        }
      }
    } catch (e) {}
    return cols.filter(Boolean);
  }

  function sampleDataset(ds) {
    const columns = getColumns(ds);
    const rows = [];
    const count = ds.getRowCount ? ds.getRowCount() : 0;
    for (let r = 0; r < Math.min(count, sampleRows); r++) {
      const row = {};
      columns.slice(0, 40).forEach(function(col) {
        try { row[col] = ds.getValue(r, col); } catch (e) {}
      });
      rows.push(row);
    }
    return {
      id: ds.id || "",
      type: ds.type || "",
      rowCount: count,
      columns: columns,
      sampleRows: rows
    };
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
    } catch (e) {
      controls.push({error: e.message});
    }

    try {
      const dataControls = ai.getAllDataControls ? ai.getAllDataControls() : [];
      dataControls.forEach(function(dc) {
        if (dc && dc.type === "dataset") datasets.push(sampleDataset(dc));
      });
    } catch (e) {
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
            has_cpr = driver.execute_script("return typeof cpr !== 'undefined';")
            if has_cpr and "vpn" not in driver.current_url.lower():
                return True
        except Exception:
            pass
    return False


def parse_keywords(value: str | None) -> list[str]:
    if not value:
        return DEFAULT_KEYWORDS
    return [part.strip() for part in value.split(",") if part.strip()]


def write_json(prefix: str, data: dict) -> Path:
    out_dir = Path(__file__).parent
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = out_dir / f"{prefix}_{stamp}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def print_menu_matches(matches: list[dict], limit: int) -> None:
    print(f"\n[menu] 후보 {len(matches)}건")
    for i, item in enumerate(matches[:limit], start=1):
        path = item.get("path") or "(path 없음)"
        page = item.get("pageId") or item.get("callPage") or "(page 없음)"
        hits = ",".join(item.get("hits") or [])
        print(f"{i:02d}. {item.get('menuName')} | {path} | {page} | hits={hits}")
    if len(matches) > limit:
        print(f"... {len(matches) - limit}건 더 있음. JSON 덤프를 확인하세요.")


def main() -> int:
    parser = argparse.ArgumentParser(description="NEIS beginning-of-semester menu explorer")
    parser.add_argument("--port", type=int, default=REMOTE_PORT)
    parser.add_argument("--keywords", help="Comma-separated Korean menu keywords")
    parser.add_argument("--menu", help="Menu name to open after listing candidates")
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--sample-rows", type=int, default=3)
    parser.add_argument("--no-dump", action="store_true", help="Skip active app structure dump")
    args = parser.parse_args()

    try:
        driver = attach_chrome(args.port)
    except Exception as exc:
        print(f"[connect:error] 127.0.0.1:{args.port} Chrome에 연결하지 못했습니다: {exc}")
        print("먼저 사용자 화면에서 9222 디버깅 Chrome을 열고 나이스에 로그인해 주세요.")
        return 2

    if not switch_to_neis_cpr_window(driver):
        print("[connect:error] cpr Platform이 있는 나이스 화면을 찾지 못했습니다.")
        print("나이스 로그인 완료 후 메인 화면에서 다시 실행해 주세요.")
        return 3

    print(f"[connect] {driver.title}")
    print(f"[url] {driver.current_url}")

    keywords = parse_keywords(args.keywords)
    menu_result = driver.execute_script(JS_FIND_MENUS, keywords)
    if menu_result.get("error"):
        print("[menu:error]", menu_result["error"])
        return 4

    matches = menu_result.get("matches", [])
    print_menu_matches(matches, args.limit)
    menu_path = write_json("semester_start_menu_candidates", {"keywords": keywords, "matches": matches})
    print(f"[menu:json] {menu_path}")

    if args.menu:
        print(f"\n[navigate] 메뉴 검색/접속 시도: {args.menu}")
        search_result = driver.execute_script(JS_SEARCH_MENU, args.menu)
        print("[navigate:search]", search_result)
        time.sleep(2.0)
        click_result = driver.execute_script(JS_CLICK_MENU_TEXT, args.menu)
        print("[navigate:click]", click_result)
        time.sleep(4.0)

    if not args.no_dump:
        dump = driver.execute_script(JS_DUMP_ACTIVE_APPS, args.sample_rows)
        dump_path = write_json("semester_start_active_apps", dump)
        print(f"[apps:json] {dump_path}")
        if dump.get("apps"):
            print("\n[apps] 실행 중 앱")
            for app in dump["apps"]:
                datasets = ", ".join(
                    f"{ds.get('id')}({ds.get('rowCount')})"
                    for ds in app.get("datasets", [])
                    if ds.get("id")
                )
                print(f"- {app.get('appId')} | controls={app.get('controlsCount')} | datasets={datasets}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
