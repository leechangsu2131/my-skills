#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""결재선 입력 오류 이후의 최종 상신 처리 스크립트."""

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

def dismiss_confirm_alert(driver, action_name=""):
    js = """
    var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var target = null;
    instances.forEach(function(ai) {
        if (!ai || !ai.app) return;
        var aid = ai.app.id || "";
        if (aid === "app/cmn/confirm" || aid === "app/cmn/alert") {
            target = ai;
        }
    });
    if (!target) return {found: false};
    
    var msg = "";
    var btn = null;
    target.getContainer().getAllRecursiveChildren().forEach(function(ctrl) {
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
        var appId = (target.app && target.app.id) ? target.app.id : "unknown";
        return {found: true, appId: appId, msg: msg, clicked: btn.id || btn.value};
    }
    var appId2 = (target.app && target.app.id) ? target.app.id : "unknown";
    return {found: true, appId: appId2, msg: msg, error: "btn not found"};
    """
    res = driver.execute_script(js)
    if res.get("found"):
        print(f"  [modal-{action_name}] 팝업 발견({res.get('appId')}): {res.get('msg')} -> 클릭: {res.get('clicked')}")
        time.sleep(1.5)
        return True
    return False

# 1) 열려 있는 Alert 팝업을 먼저 수락해 닫습니다.
print("\n1. 현재 열린 경고창(Alert/Confirm) 닫기 시도...")
dismiss_confirm_alert(driver, "초기경고닫기")
time.sleep(1.5)

# 2) 만약 결재자지정 팝업이 아직 닫히지 않았다면 [저장] 클릭
js_check_pop = """
var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
var pop = instances.find(function(ai) {
    return ai && ai.app && ai.app.id === "edu/cm/wam/woa/pm/wam_woapm07_p04";
});
if (pop) {
    var btnSave = pop.lookup("btn4");
    if (btnSave) {
        btnSave.click();
        return {ok: true, message: "clicked save on p04"};
    }
}
return {ok: false, message: "p04 not open"};
"""
res_pop = driver.execute_script(js_check_pop)
print("  결재자지정 팝업 체크 결과:", res_pop)
if res_pop.get("ok"):
    time.sleep(2.0)
    dismiss_confirm_alert(driver, "p04저장후")

# 3) 최종 상신 버튼 클릭
print("\n2. 기안문서상신 최종 [상신] 버튼 클릭...")
js_drft = """
var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
var drftApp = instances.find(function(ai) {
    return ai && ai.app && ai.app.id === "edu/cm/wam/woa/pm/wam_woapm07_p00";
});
if (!drftApp) return {error: "wam_woapm07_p00 app not found"};

var btnDrft = drftApp.lookup("btnDrft");
if (btnDrft) {
    btnDrft.click();
    return {ok: true};
}
return {error: "btnDrft not found"};
"""
res_drft = driver.execute_script(js_drft)
print("  상신 결과:", res_drft)
time.sleep(2.5)

# 최종 확인 및 알림 창 순차 처리
print("\n3. 최종 확인 모달창 처리...")
for i in range(4):
    if dismiss_confirm_alert(driver, f"최종상신승인-{i+1}"):
        time.sleep(1.5)
    else:
        time.sleep(1.0)

print("\n=== [완료] 상신 최종 처리 완료! ===")
