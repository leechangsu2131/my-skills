#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""교외체험학습 데이터셋/그리드 상세 진단 스크립트."""

import io, sys, json
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

opts = Options()
opts.add_experimental_option("debuggerAddress", "localhost:9222")
driver = webdriver.Chrome(options=opts)
print(f"[connect] {driver.title}")

# NEIS 창으로 전환
for handle in driver.window_handles:
    driver.switch_to.window(handle)
    driver.switch_to.default_content()
    try:
        has_cpr = driver.execute_script("return typeof cpr !== 'undefined';")
        if has_cpr:
            url = driver.current_url
            if "vpn" not in url.lower():
                print(f"[window] NEIS: {driver.title}")
                break
    except:
        pass

JS = r"""
return (function() {
  var inst = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "edu/sa/eds/eaa/ae/eds_eaaae01_m01";
  });
  if (!inst) return {error: "app not found"};

  // 1) dsStdntListForAply 상세
  var ds = inst.lookup("dsStdntListForAply");
  var cols = [];
  if (ds) {
    try {
      for (var i = 0; i < ds.getColumnCount(); i++) {
        var c = ds.getColumn(i);
        cols.push(c && (c.columnName || c.name || String(c)));
      }
    } catch(e) { cols.push("ERR:" + e.message); }
  }

  var rows = [];
  if (ds) {
    for (var r = 0; r < Math.min(ds.getRowCount(), 10); r++) {
      var row = {};
      cols.forEach(function(col) {
        try { row[col] = ds.getValue(r, col); } catch(e) {}
      });
      rows.push(row);
    }
  }

  // 2) grdMain 정보
  var grid = inst.lookup("grdMain");
  var gridInfo = {};
  if (grid) {
    gridInfo.constructorName = grid.constructor ? grid.constructor.name : "unknown";
    gridInfo.type = grid.type || "";
    // 그리드에서 사용 가능한 메서드 확인
    var methods = [];
    try {
      var proto = Object.getPrototypeOf(grid);
      Object.getOwnPropertyNames(proto).forEach(function(m) {
        if (m.indexOf("get") === 0 || m.indexOf("click") === 0 ||
            m.indexOf("select") === 0 || m.indexOf("check") === 0 ||
            m.indexOf("Row") >= 0 || m.indexOf("Cell") >= 0) {
          methods.push(m);
        }
      });
    } catch(e) { methods.push("ERR:" + e.message); }
    gridInfo.methods = methods.slice(0, 40);
  }

  // 3) 버튼 목록
  var btns = [];
  inst.getContainer().getAllRecursiveChildren().forEach(function(c) {
    if (c.type === "button") {
      btns.push({id: c.id || "", val: c.value || c.text || ""});
    }
  });

  // 4) 조회 버튼 찾기 (lookup 시도)
  var searchBtn = inst.lookup("btnSearch");
  var searchBtnInfo = searchBtn ? {id: searchBtn.id, val: searchBtn.value || searchBtn.text || ""} : null;

  return {
    cols: cols,
    rowCount: ds ? ds.getRowCount() : -1,
    rows: rows,
    gridInfo: gridInfo,
    buttons: btns,
    searchBtn: searchBtnInfo
  };
})();
"""

result = driver.execute_script(JS)
print(json.dumps(result, ensure_ascii=False, indent=2))
