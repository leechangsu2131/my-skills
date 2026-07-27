#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""보고서관리 및 결석신고서관리 상세조회 팝업 앱 구조 진단 스크립트."""

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

# 1) 교외체험학습보고서관리에서 박서우(Index 0) 클릭 및 팝업 덤프
JS_REPORT_POPUP = r"""
return (function() {
    var inst = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
        return ai.app && ai.app.id === "edu/sa/eds/eaa/ae/eds_eaaae02_m01";
    });
    if (!inst) return {error: "eds_eaaae02_m01 app not found"};
    
    var grid = inst.lookup("grdMain");
    var ds = inst.lookup("dsStdntListForRlt");
    if (!grid || !ds) return {error: "grid/ds not found"};
    
    var name = ds.getValue(0, "stuFlnm"); // "박서우"
    grid.selectRows([0]);
    
    // DOM 찾아서 성명 셀 클릭
    var gridEl = document.getElementById("uuid-" + grid.uuid);
    if (!gridEl) return {error: "grid DOM element not found"};
    
    var rowEl = gridEl.querySelector('[data-rowindex="0"]');
    if (!rowEl) return {error: "row DOM not found"};
    
    var targetSpan = null;
    var candidates = rowEl.querySelectorAll('span, div, td, a');
    for (var i = 0; i < candidates.length; i++) {
        if (candidates[i].innerText.trim() === name) {
            targetSpan = candidates[i];
            break;
        }
    }
    if (!targetSpan) return {error: "span with text " + name + " not found"};
    
    targetSpan.click();
    return {ok: true};
})();
"""

print("\n=== [교외체험학습보고서관리] 상세 팝업 열기 시도 ===")
res_rep_pop = driver.execute_script(JS_REPORT_POPUP)
print("  결과:", res_rep_pop)
time.sleep(3.0)

# 현재 팝업 인스턴스 덤프
JS_DIAGNOSE_POPUPS = r"""
var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
var popups = [];
instances.forEach(function(ai) {
    var aid = ai.app ? ai.app.id : "";
    if (aid !== "app/com/main/Index" && aid !== "app/com/main/Dashboard3" && aid.indexOf("eaaae0") === -1 && aid.indexOf("udc") === -1) {
        var ctrls = [];
        ai.getContainer().getAllRecursiveChildren().forEach(function(c) {
            ctrls.push({id: c.id || "", type: c.type || "", val: c.value || c.text || ""});
        });
        popups.push({appId: aid, title: ai.title || "", controls: ctrls});
    }
});
return popups;
"""
res_popups1 = driver.execute_script(JS_DIAGNOSE_POPUPS)
print("  탐색된 상세 팝업들:", [p["appId"] for p in res_popups1])
for p in res_popups1:
    print(f"    [app] {p['appId']}")
    for c in p["controls"]:
        if c["val"] in ["저장", "접수", "닫기"] or c["type"] == "button":
            print(f"      - {c['id']} ({c['type']}): '{c['val']}'")

# 팝업 닫기 (닫기 버튼 클릭)
JS_CLOSE_CURRENT_POP = r"""
var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
var closed = false;
instances.forEach(function(ai) {
    var aid = ai.app ? ai.app.id : "";
    if (aid !== "app/com/main/Index" && aid.indexOf("eaaae0") === -1) {
        ai.getContainer().getAllRecursiveChildren().forEach(function(c) {
            var val = c.value || c.text || "";
            if (val === "닫기" && !closed) {
                c.click();
                closed = true;
            }
        });
    }
});
return closed;
"""
driver.execute_script(JS_CLOSE_CURRENT_POP)
time.sleep(2.0)


# 2) 결석신고서관리에서 김주안(Index 0) 클릭 및 팝업 덤프
JS_ABSENCE_POPUP = r"""
return (function() {
    var inst = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
        return ai.app && ai.app.id === "edu/sa/eds/eaa/ae/eds_eaaae03_m01";
    });
    if (!inst) return {error: "eds_eaaae03_m01 app not found"};
    
    var grid = inst.lookup("grdMain");
    var ds = inst.lookup("dsStdntListForAbe");
    if (!grid || !ds) return {error: "grid/ds not found"};
    
    var name = ds.getValue(0, "stuFlnm"); // "김주안"
    grid.selectRows([0]);
    
    var gridEl = document.getElementById("uuid-" + grid.uuid);
    if (!gridEl) return {error: "grid DOM element not found"};
    
    var rowEl = gridEl.querySelector('[data-rowindex="0"]');
    if (!rowEl) return {error: "row DOM not found"};
    
    var targetSpan = null;
    var candidates = rowEl.querySelectorAll('span, div, td, a');
    for (var i = 0; i < candidates.length; i++) {
        if (candidates[i].innerText.trim() === name) {
            targetSpan = candidates[i];
            break;
        }
    }
    if (!targetSpan) return {error: "span with text " + name + " not found"};
    
    targetSpan.click();
    return {ok: true};
})();
"""

print("\n=== [결석신고서관리] 상세 팝업 열기 시도 ===")
res_abs_pop = driver.execute_script(JS_ABSENCE_POPUP)
print("  결과:", res_abs_pop)
time.sleep(3.0)

res_popups2 = driver.execute_script(JS_DIAGNOSE_POPUPS)
print("  탐색된 상세 팝업들:", [p["appId"] for p in res_popups2])
for p in res_popups2:
    print(f"    [app] {p['appId']}")
    for c in p["controls"]:
        if c["val"] in ["저장", "접수", "닫기"] or c["type"] == "button":
            print(f"      - {c['id']} ({c['type']}): '{c['val']}'")

# 팝업 닫기 (닫기 버튼 클릭)
driver.execute_script(JS_CLOSE_CURRENT_POP)
time.sleep(1.5)
