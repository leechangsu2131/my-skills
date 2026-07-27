#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""경고 Alert을 닫은 후 결재선 팝업을 진단하는 스크립트."""

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

# 1) 현재 열린 Alert 팝업 닫기
JS_DISMISS_ALERT = """
var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
var alertApp = instances.find(function(ai) {
    return ai && ai.app && ai.app.id === "app/cmn/alert";
});
if (!alertApp) return "no alert found";

// alert 메시지 덤프
var msg = "";
var btn = null;
alertApp.getContainer().getAllRecursiveChildren().forEach(function(ctrl) {
    var type = ctrl.type || "";
    var val = ctrl.value || ctrl.text || "";
    if (type === "output" || type === "htmlsnippet") {
        msg += " | " + val;
    }
    if (val === "확인" || ctrl.id === "btnOk" || ctrl.id === "btnConfirm") {
        btn = ctrl;
    }
});

if (btn) {
    btn.click();
    return {ok: true, msg: msg, clicked: btn.id || btn.value};
}
return {error: "btn not found", msg: msg};
"""

res_alert = driver.execute_script(JS_DISMISS_ALERT)
print("Alert 팝업 처리 결과:", res_alert)
time.sleep(3.0) # 결재선 팝업 로딩 대기

# 2) 결재선 팝업이 떴는지 탐색 및 덤프
JS_DIAGNOSE_APPROVAL = """
var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
var appList = [];
instances.forEach(function(ai, idx) {
    if (!ai || !ai.app) return;
    var container = ai.getContainer();
    var ctrls = [];
    container.getAllRecursiveChildren().forEach(function(ctrl) {
        var val = (ctrl.value || ctrl.text || ctrl.fieldLabel || "").toString().substring(0, 50);
        ctrls.push({id: ctrl.id || "", type: ctrl.type || "", val: val});
    });
    
    var datasets = [];
    var dc = ai.getAllDataControls ? ai.getAllDataControls() : [];
    dc.forEach(function(ds) {
        datasets.push({id: ds.id || "", rowCount: ds.getRowCount ? ds.getRowCount() : null});
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

res_apps = driver.execute_script(JS_DIAGNOSE_APPROVAL)
print("\n=== 결재선 팝업 진단 결과 ===")
for app in res_apps:
    # com/main/Index나 Dashboard 등 핵심을 제외한 팝업을 자세히 덤프
    app_id = app["appId"]
    if "Index" not in app_id and "Dashboard" not in app_id and "eaa01_m01" not in app_id:
        print(f"[app] {app_id} | title: '{app['title']}'")
        print("  [Datasets]")
        for ds in app["datasets"]:
            print(f"    - {ds['id']} (rows: {ds['rowCount']})")
        print("  [Controls]")
        # 주요 버튼이나 입력창 위주로 출력
        for ctrl in app["controls"]:
            t = ctrl["type"]
            val = ctrl["val"]
            cid = ctrl["id"]
            if t == "button" or t == "inputbox" or t == "grid" or val:
                print(f"    - ID: {cid} | Type: {t} | Val: '{val}'")
