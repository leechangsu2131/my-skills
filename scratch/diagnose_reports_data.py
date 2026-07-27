#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""보고서관리 및 결석신고서관리 데이터셋 행 상세 진단 스크립트."""

import io, sys, time, json
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

opts = Options()
opts.add_experimental_option("debuggerAddress", "localhost:9222")
driver = webdriver.Chrome(options=opts)

for handle in driver.window_handles:
    driver.switch_to.window(handle)
    driver.switch_to.default_content()
    try:
        if driver.execute_script("return typeof cpr !== 'undefined';") and "vpn" not in driver.current_url.lower():
            break
    except: pass

print(f"[connect] {driver.title}")

# 1) 교외체험학습보고서관리 (eds_eaaae02_m01) 조회 클릭 후 데이터셋 덤프
JS_DUMP_REPORT = r"""
return (function() {
    var inst = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
        return ai.app && ai.app.id === "edu/sa/eds/eaa/ae/eds_eaaae02_m01";
    });
    if (!inst) return {error: "eaaae02 app not found"};
    
    // 조회 클릭
    var btnSearch = inst.lookup("btnSearch");
    if (btnSearch) btnSearch.click();
    
    // 1초 대기 후 로우 덤프
    var ds = inst.lookup("dsStdntListForRlt");
    if (!ds) return {error: "dsStdntListForRlt not found"};
    
    var colNames = ds.getColumnNames();
    var rows = [];
    for (var r = 0; r < ds.getRowCount(); r++) {
        var row = {};
        colNames.forEach(function(col) {
            row[col] = ds.getValue(r, col);
        });
        rows.push(row);
    }
    return {colNames: colNames, rows: rows};
})();
"""

res_report = driver.execute_script(JS_DUMP_REPORT)
print("\n=== [교외체험학습보고서관리] 데이터셋 ===")
if "error" in res_report:
    print(res_report)
else:
    print(f"전체 {len(res_report['rows'])}건:")
    for r in res_report["rows"]:
        print(f"  - 학생: {r.get('stuFlnm')} (번호: {r.get('clsNo')}) | 처리상태: {r.get('eduActPrcsStsNm')} | 상신상태: {r.get('atrzStsNm')} | 체험기간: {r.get('experLrnPeriod')}")

# 2) 결석신고서관리 (eds_eaaae03_m01) 조회 클릭 후 데이터셋 덤프
JS_DUMP_ABSENCE = r"""
return (function() {
    var inst = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
        return ai.app && ai.app.id === "edu/sa/eds/eaa/ae/eds_eaaae03_m01";
    });
    if (!inst) return {error: "eaaae03 app not found"};
    
    // 조회 클릭
    var btnSearch = inst.lookup("btnSearch");
    if (btnSearch) btnSearch.click();
    
    // 1초 대기 후 로우 덤프
    var ds = inst.lookup("dsStdntListForAbe");
    if (!ds) return {error: "dsStdntListForAbe not found"};
    
    var colNames = ds.getColumnNames();
    var rows = [];
    for (var r = 0; r < ds.getRowCount(); r++) {
        var row = {};
        colNames.forEach(function(col) {
            row[col] = ds.getValue(r, col);
        });
        rows.push(row);
    }
    return {colNames: colNames, rows: rows};
})();
"""

time.sleep(1.5)
res_absence = driver.execute_script(JS_DUMP_ABSENCE)
print("\n=== [결석신고서관리] 데이터셋 ===")
if "error" in res_absence:
    print(res_absence)
else:
    print(f"전체 {len(res_absence['rows'])}건:")
    for r in res_absence["rows"]:
        print(f"  - 학생: {r.get('stuFlnm')} (번호: {r.get('clsNo')}) | 처리상태: {r.get('eduActPrcsStsNm') or r.get('eduActPrcsStsCd')} | 상신상태: {r.get('atrzStsNm') or r.get('atrzStsCd')} | 결석기간: {r.get('absncBgngDt')} ~ {r.get('absncEndDt')}")

# JSON 덤프로 전체 데이터 백업
with open("scratch/reports_data_dump.json", "w", encoding="utf-8") as f:
    json.dump({"report": res_report, "absence": res_absence}, f, ensure_ascii=False, indent=2)
