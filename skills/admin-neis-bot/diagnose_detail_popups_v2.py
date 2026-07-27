#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""탭 활성화를 포함한 상세조회 팝업 구조 정밀 진단 스크립트."""

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

# 탭 활성화 함수
def activate_tab(driver, tab_name: str):
    js = """
    var tabs = document.querySelectorAll('.cl-tabfolder-item, [role="tab"], .cl-tab, a, span');
    var clicked = false;
    for (var i = 0; i < tabs.length; i++) {
        var text = (tabs[i].innerText || tabs[i].textContent || "").trim();
        if (text === "TARGET") {
            tabs[i].click();
            clicked = true;
            break;
        }
    }
    return clicked;
    """.replace("TARGET", tab_name)
    res = driver.execute_script(js)
    print(f"  [{tab_name}] 탭 활성화 시도 결과: {res}")
    time.sleep(1.5)

# 팝업 닫기
def close_popup(driver):
    js = """
    var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var closed = false;
    instances.forEach(function(ai) {
        var aid = ai.app ? ai.app.id : "";
        if (aid !== "app/com/main/Index" && aid.indexOf("_m01") === -1) {
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
    driver.execute_script(js)
    time.sleep(1.5)

# 1) 교외체험학습보고서관리 (eds_eaaae02_m01) 진단
print("\n=== 1. 교외체험학습보고서관리 상세 팝업 진단 ===")
activate_tab(driver, "교외체험학습보고서관리")

JS_CLICK_STUDENT_REPORT = """
var inst = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "edu/sa/eds/eaa/ae/eds_eaaae02_m01";
});
if (!inst) return {error: "eds_eaaae02_m01 app not found"};

var grid = inst.lookup("grdMain");
var ds = inst.lookup("dsStdntListForRlt");
if (!grid || !ds) return {error: "grid/ds not found"};

var name = ds.getValue(0, "stuFlnm");
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
"""
res_rep = driver.execute_script(JS_CLICK_STUDENT_REPORT)
print("  박서우 클릭 시도:", res_rep)
time.sleep(2.5)

# 팝업 덤프 (필터링 느슨하게)
JS_DIAGNOSE_POPUPS_ALL = """
var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
var popups = [];
instances.forEach(function(ai) {
    var aid = ai.app ? ai.app.id : "";
    // 메인화면과 탭 화면들을 제외한 팝업창들만 수집
    if (aid !== "app/com/main/Index" && aid !== "app/com/main/Dashboard3" && aid.indexOf("_m01") === -1 && aid.indexOf("udc") === -1) {
        var ctrls = [];
        ai.getContainer().getAllRecursiveChildren().forEach(function(c) {
            ctrls.push({id: c.id || "", type: c.type || "", val: c.value || c.text || ""});
        });
        popups.push({appId: aid, title: ai.title || "", controls: ctrls});
    }
});
return popups;
"""
res_popups1 = driver.execute_script(JS_DIAGNOSE_POPUPS_ALL)
print("  탐색된 팝업:", [p["appId"] for p in res_popups1])
for p in res_popups1:
    print(f"    [app] {p['appId']}")
    for c in p["controls"]:
        if c["val"] in ["저장", "접수", "닫기"] or c["type"] == "button":
            print(f"      - {c['id']} ({c['type']}): '{c['val']}'")

# 팝업 닫기
close_popup(driver)


# 2) 결석신고서관리 (eds_eaaae03_m01) 진단
print("\n=== 2. 결석신고서관리 상세 팝업 진단 ===")
activate_tab(driver, "결석신고서관리")

JS_CLICK_STUDENT_ABSENCE = """
var inst = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "edu/sa/eds/eaa/ae/eds_eaaae03_m01";
});
if (!inst) return {error: "eds_eaaae03_m01 app not found"};

var grid = inst.lookup("grdMain");
var ds = inst.lookup("dsStdntListForAbe");
if (!grid || !ds) return {error: "grid/ds not found"};

var name = ds.getValue(0, "stuFlnm");
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
"""
res_abs = driver.execute_script(JS_CLICK_STUDENT_ABSENCE)
print("  김주안 클릭 시도:", res_abs)
time.sleep(2.5)

res_popups2 = driver.execute_script(JS_DIAGNOSE_POPUPS_ALL)
print("  탐색된 팝업:", [p["appId"] for p in res_popups2])
for p in res_popups2:
    print(f"    [app] {p['appId']}")
    for c in p["controls"]:
        if c["val"] in ["저장", "접수", "닫기"] or c["type"] == "button":
            print(f"      - {c['id']} ({c['type']}): '{c['val']}'")

# 팝업 닫기
close_popup(driver)
