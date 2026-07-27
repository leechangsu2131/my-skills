#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""결재자지정 버튼을 클릭하고 새로 생성된 결재자 선택 팝업을 진단하는 스크립트."""

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

# 1) 기안문서상신 앱에서 [결재자지정] (btnSelectSancr) 클릭
JS_CLICK_SELECT_SANCR = """
var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
var drftApp = instances.find(function(ai) {
    return ai && ai.app && ai.app.id === "edu/cm/wam/woa/pm/wam_woapm07_p00";
});
if (!drftApp) return {error: "wam_woapm07_p00 (기안문서상신) app not found"};

var btn = drftApp.lookup("btnSelectSancr");
if (btn) {
    btn.click();
    return {ok: true, clicked: "btnSelectSancr"};
}
return {error: "btnSelectSancr control not found"};
"""

res_click = driver.execute_script(JS_CLICK_SELECT_SANCR)
print("결재자지정 클릭 결과:", res_click)

if res_click.get("ok"):
    print("3초 대기 (결재자 지정 팝업 로딩)...")
    time.sleep(3.0)
else:
    sys.exit("결재자지정 버튼을 클릭하지 못했습니다.")

# 2) 결재자 지정 팝업 덤프 및 진단
JS_DIAGNOSE_SANCR_POP = """
var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
var appList = [];
instances.forEach(function(ai, idx) {
    if (!ai || !ai.app) return;
    
    var container = ai.getContainer();
    var ctrls = [];
    container.getAllRecursiveChildren().forEach(function(ctrl) {
        var val = (ctrl.value || ctrl.text || ctrl.fieldLabel || "").toString().substring(0, 80);
        ctrls.push({id: ctrl.id || "", type: ctrl.type || "", val: val});
    });
    
    var datasets = [];
    var dc = ai.getAllDataControls ? ai.getAllDataControls() : [];
    dc.forEach(function(ds) {
        var cols = [];
        try {
            if (ds.getColumnNames) cols = ds.getColumnNames();
        } catch(e) {}
        datasets.push({id: ds.id || "", rowCount: ds.getRowCount ? ds.getRowCount() : null, cols: cols.slice(0, 10)});
    });
    
    appList.push({
        idx: idx,
        appId: ai.app.id,
        title: ai.title || "",
        controls: ctrls,
        datasets: datasets
    });
});
return appList;
"""

res_apps = driver.execute_script(JS_DIAGNOSE_SANCR_POP)
print("\n=== 결재자 검색/지정 팝업 분석 결과 ===")
for app in res_apps:
    app_id = app["appId"]
    # 메인 앱들을 제외하고 방금 새로 뜬 팝업만 자세히 덤프
    if "Index" not in app_id and "Dashboard" not in app_id and "eaa01_m01" not in app_id and "wam_woapm01_p02" not in app_id and "udcCal" not in app_id:
        print(f"\n[app] {app_id} | Title: '{app['title']}'")
        print("  [Datasets]")
        for ds in app["datasets"]:
            print(f"    - {ds['id']} (rows: {ds['rowCount']}) | cols: {ds['cols']}")
        print("  [Controls]")
        for ctrl in app["controls"]:
            t = ctrl["type"]
            val = ctrl["val"]
            cid = ctrl["id"]
            if t == "button" or t == "inputbox" or t == "grid" or val:
                print(f"    - ID: {cid} | Type: {t} | Val: '{val}'")
