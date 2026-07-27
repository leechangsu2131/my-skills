#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""컨펌창을 승인하고 로드되는 결재선 팝업 구조를 상세 진단하는 스크립트."""

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

# 1) 컨펌창 승인 클릭
JS_DISMISS_CONFIRM = """
var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
var confApp = instances.find(function(ai) {
    return ai && ai.app && ai.app.id === "app/cmn/confirm";
});
if (!confApp) return "no confirm popup active";

var msg = "";
var btn = null;
confApp.getContainer().getAllRecursiveChildren().forEach(function(ctrl) {
    var val = ctrl.value || ctrl.text || "";
    if (ctrl.type === "output" || ctrl.type === "htmlsnippet") {
        msg += " | " + val;
    }
    if (val === "확인" || val === "예" || ctrl.id === "btnOk" || ctrl.id === "btnConfirm") {
        btn = ctrl;
    }
});

if (btn) {
    btn.click();
    return {ok: true, msg: msg, clicked: btn.id || btn.value};
}
return {error: "confirm button not found", msg: msg};
"""

res_conf = driver.execute_script(JS_DISMISS_CONFIRM)
print("컨펌창 처리 결과:", res_conf)

if res_conf == "no confirm popup active" or (isinstance(res_conf, dict) and res_conf.get("ok")):
    print("3초 대기 (결재선 지정 팝업 로딩)...")
    time.sleep(3.0)
else:
    sys.exit("컨펌창을 닫지 못했습니다.")

# 2) 새로 뜬 결재선 팝업 진단
JS_DIAGNOSE_APR_POP = """
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

res_apps = driver.execute_script(JS_DIAGNOSE_APR_POP)
print("\n=== 결재선 지정 팝업 분석 결과 ===")
for app in res_apps:
    app_id = app["appId"]
    # 메인 구성 탭을 제외한 결재선 관련 팝업만 필터
    if "Index" not in app_id and "Dashboard" not in app_id and "eaa01_m01" not in app_id and "udcCal" not in app_id:
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
