#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""컬럼명을 정확히 찾고, 그리드 행을 getValue로 데이터 추출하는 진단 스크립트."""

import io, sys, json
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

opts = Options()
opts.add_experimental_option("debuggerAddress", "localhost:9222")
driver = webdriver.Chrome(options=opts)

# NEIS 창으로 전환
for handle in driver.window_handles:
    driver.switch_to.window(handle)
    driver.switch_to.default_content()
    try:
        has_cpr = driver.execute_script("return typeof cpr !== 'undefined';")
        if has_cpr and "vpn" not in driver.current_url.lower():
            break
    except:
        pass

# 조회 먼저 클릭
print("=== 조회 클릭 ===")
click_res = driver.execute_script(r"""
var inst = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "edu/sa/eds/eaa/ae/eds_eaaae01_m01";
});
if (!inst) return "no app";
var btn = inst.lookup("btnSearch");
if (!btn) return "no btnSearch";
btn.click();
return "clicked";
""")
print(f"  결과: {click_res}")

import time
time.sleep(2)

# 데이터셋 컬럼 탐색 (다양한 방식 시도)
print("\n=== 데이터셋 컬럼 탐색 ===")
result = driver.execute_script(r"""
var inst = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "edu/sa/eds/eaa/ae/eds_eaaae01_m01";
});
if (!inst) return {error: "app not found"};
var ds = inst.lookup("dsStdntListForAply");
if (!ds) return {error: "ds not found"};

var result = {};
result.rowCount = ds.getRowCount();

// 방법 1: getColumnNames
try { result.colNames = ds.getColumnNames ? ds.getColumnNames() : "no method"; } catch(e) { result.colNames_err = e.message; }

// 방법 2: getColumn(i) 의 다양한 속성
var colDetails = [];
try {
    for (var i = 0; i < ds.getColumnCount(); i++) {
        var c = ds.getColumn(i);
        if (!c) { colDetails.push({i: i, val: null}); continue; }
        var d = {i: i};
        try { d.columnName = c.columnName; } catch(e) {}
        try { d.name = c.name; } catch(e) {}
        try { d.id = c.id; } catch(e) {}
        try { d.toString = String(c); } catch(e) {}
        try { d.header = c.header; } catch(e) {}
        try { d.keys = Object.keys(c).slice(0, 10); } catch(e) {}
        colDetails.push(d);
    }
} catch(e) { colDetails.push({err: e.message}); }
result.colDetails = colDetails.slice(0, 15);

// 방법 3: 첫 행의 데이터를 통째로 가져오기
try {
    var row0 = ds.getRowData ? ds.getRowData(0) : null;
    if (row0) {
        result.row0keys = Object.keys(row0);
        result.row0sample = {};
        Object.keys(row0).forEach(function(k) {
            result.row0sample[k] = String(row0[k]).substring(0, 50);
        });
    }
} catch(e) { result.row0_err = e.message; }

// 방법 4: 그리드의 헤더 정보
var grid = inst.lookup("grdMain");
if (grid) {
    try {
        var headers = [];
        var row = grid.getRow(0);
        if (row) {
            result.row0_type = row.constructor ? row.constructor.name : "unknown";
            result.row0_keys = Object.keys(row).slice(0, 20);
        }
    } catch(e) { result.gridRow_err = e.message; }
    
    try {
        var dataRow = grid.getDataRow(0);
        if (dataRow) {
            result.dataRow0 = {};
            Object.keys(dataRow).forEach(function(k) {
                result.dataRow0[k] = String(dataRow[k]).substring(0, 50);
            });
        }
    } catch(e) { result.dataRow0_err = e.message; }
}

return result;
""")

print(json.dumps(result, ensure_ascii=False, indent=2))
