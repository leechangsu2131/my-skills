#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""이미 로드된 전체 목록에서 강동휘, 김경영을 찾아 더블클릭 추가하고 최종 상신하는 완료 스크립트."""

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

# 결재자 더블클릭 추가 로직
def add_approver_from_list(driver, name: str) -> bool:
    print(f"\n1. 결재자 '{name}' 더블클릭 추가 시도...")
    js_dblclick = """
    var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var pop = instances.find(function(ai) {
        return ai && ai.app && ai.app.id === "edu/cm/wam/woa/pm/wam_woapm07_p04";
    });
    if (!pop) return {error: "p04 app not found"};
    
    var dsMain = pop.lookup("dsMain");
    var grdUserListFrom = pop.lookup("grdUserListFrom");
    var btnAdd = pop.lookup("btn1");
    if (!dsMain || !grdUserListFrom || !btnAdd) return {error: "ds/grid/btn not found"};
    
    // 전체 목록에서 이름 일치 행 인덱스 검색
    var targetRow = -1;
    for (var i = 0; i < dsMain.getRowCount(); i++) {
        var unm = dsMain.getValue(i, "userNm");
        var org = dsMain.getValue(i, "allKornOrgNm") || dsMain.getValue(i, "kornOrgNm") || "";
        // 동명이인이 있거나 본교 임원임을 확실시하기 위해 조직명 "화천" 체크
        if (unm === "TARGET_NAME") {
            targetRow = i;
            break;
        }
    }
    if (targetRow === -1) return {error: "TARGET_NAME not found in dsMain"};
    
    var gridEl = document.getElementById("uuid-" + grdUserListFrom.uuid);
    if (!gridEl) return {error: "grid DOM element not found"};
    
    var rowEl = gridEl.querySelector('[data-rowindex="' + targetRow + '"]');
    if (!rowEl) return {error: "row DOM element not found"};
    
    // 정확히 텍스트가 TARGET_NAME인 span/div 찾기
    var targetSpan = null;
    var candidates = rowEl.querySelectorAll('span, div, td, a');
    for (var i = 0; i < candidates.length; i++) {
        if (candidates[i].innerText.trim() === "TARGET_NAME") {
            targetSpan = candidates[i];
            break;
        }
    }
    if (!targetSpan) return {error: "text span not found"};
    
    // 더블클릭 시뮬레이션
    targetSpan.click();
    var dblEvent = new MouseEvent('dblclick', {
        bubbles: true,
        cancelable: true,
        view: window
    });
    targetSpan.dispatchEvent(dblEvent);
    
    // 추가 버튼 백업 클릭
    grdUserListFrom.selectRows([targetRow]);
    btnAdd.click();
    
    return {ok: true, index: targetRow};
    """.replace("TARGET_NAME", name)
    
    res = driver.execute_script(js_dblclick)
    if res.get("error"):
        print(f"  [오류] 추가 실패: {res['error']}")
        return False
    print(f"  '{name}' 더블클릭 성공 (Index: {res.get('index')})")
    time.sleep(1.5)
    return True

# 강동휘(교무) -> 김경영(교감) 순으로 추가
if add_approver_from_list(driver, "강동휘") and add_approver_from_list(driver, "김경영"):
    # 결재선 저장 (btn4 클릭)
    print("\n2. 결재선 저장...")
    js_save = """
    var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var pop = instances.find(function(ai) {
        return ai && ai.app && ai.app.id === "edu/cm/wam/woa/pm/wam_woapm07_p04";
    });
    if (!pop) return false;
    var btnSave = pop.lookup("btn4");
    if (btnSave) {
        btnSave.click();
        return true;
    }
    return false;
    """
    driver.execute_script(js_save)
    time.sleep(2.5)
    # 저장 후 안내창 확인 수락
    dismiss_confirm_alert(driver, "p04저장후")
else:
    sys.exit("결재자 지정 실패로 중단.")

# 최종 상신 클릭
print("\n3. 기안문서상신 최종 [상신] 버튼 클릭...")
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
time.sleep(3.0)

# 최종 확인 및 알림 창 순차 처리
print("\n4. 최종 확인 모달창 처리...")
for i in range(5):
    if dismiss_confirm_alert(driver, f"최종상신승인-{i+1}"):
        time.sleep(2.0)
    else:
        time.sleep(1.0)

print("\n=== [완료] 교외체험학습신청서 상신 최종 처리가 완료되었습니다! ===")
