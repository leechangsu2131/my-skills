#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""기안문서상신 복구 및 완결 실행 스크립트."""

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

# 1) 다이얼로그 닫기 도구
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
        return {found: true, appId: target.app.id, msg: msg, clicked: btn.id || btn.value};
    }
    return {found: true, appId: target.app.id, msg: msg, error: "btn not found"};
    """
    res = driver.execute_script(js)
    if res.get("found"):
        print(f"  [modal-{action_name}] 팝업 발견({res.get('appId')}): {res.get('msg')} -> 클릭: {res.get('clicked')}")
        time.sleep(1.5)
        return True
    return False

# 2) [결재자지정] 클릭
print("\n1. 결재자지정 버튼 클릭 시도...")
click_select_js = """
var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
var drftApp = instances.find(function(ai) {
    return ai && ai.app && ai.app.id === "edu/cm/wam/woa/pm/wam_woapm07_p00";
});
if (!drftApp) return {error: "wam_woapm07_p00 (기안문서상신) app not found"};

var btn = drftApp.lookup("btnSelectSancr");
if (btn) {
    btn.click();
    return {ok: true};
}
return {error: "btnSelectSancr not found"};
"""
res = driver.execute_script(click_select_js)
print("  결과:", res)
if not res.get("ok"):
    sys.exit("  [오류] 결재자지정 버튼을 누르지 못해 중단합니다.")

time.sleep(3.0) # 팝업 로딩 대기

# 3) 결재선 지정 팝업에서 강동휘, 김경영 순차 추가
def add_approver(driver, name: str) -> bool:
    print(f"\n2. 결재자 '{name}' 추가 진행...")
    
    # 3-1) 이름 입력 및 검색
    js_search = """
    var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var pop = instances.find(function(ai) {
        return ai && ai.app && ai.app.id === "edu/cm/wam/woa/pm/wam_woapm07_p04";
    });
    if (!pop) return {error: "wam_woapm07_p04 app not found"};
    
    var userNmInput = pop.lookup("userNm");
    var btnSearch = pop.lookup("btnSearch");
    if (!userNmInput || !btnSearch) return {error: "input or search button not found"};
    
    userNmInput.value = "TARGET_NAME";
    btnSearch.click();
    return {ok: true};
    """.replace("TARGET_NAME", name)
    
    res = driver.execute_script(js_search)
    if res.get("error"):
        print(f"  [오류] 검색 실패: {res['error']}")
        return False
    time.sleep(1.5)
    
    # 3-2) 그리드 선택 및 추가 클릭
    js_add = """
    var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var pop = instances.find(function(ai) {
        return ai && ai.app && ai.app.id === "edu/cm/wam/woa/pm/wam_woapm07_p04";
    });
    if (!pop) return {error: "wam_woapm07_p04 app not found"};
    
    var dsMain = pop.lookup("dsMain");
    var grdUserListFrom = pop.lookup("grdUserListFrom");
    var btnAdd = pop.lookup("btn1"); // 추가 버튼
    
    if (!dsMain || !grdUserListFrom || !btnAdd) return {error: "ds, grid or add button not found"};
    
    var targetRow = -1;
    for (var i = 0; i < dsMain.getRowCount(); i++) {
        var unm = dsMain.getValue(i, "userNm");
        if (unm === "TARGET_NAME") {
            targetRow = i;
            break;
        }
    }
    
    if (targetRow === -1) return {error: "name TARGET_NAME not found"};
    
    grdUserListFrom.selectRows([targetRow]);
    btnAdd.click();
    return {ok: true};
    """.replace("TARGET_NAME", name)
    
    res2 = driver.execute_script(js_add)
    if res2.get("error"):
        print(f"  [오류] 추가 실패: {res2['error']}")
        return False
    print(f"  '{name}' 추가 완료")
    time.sleep(1.0)
    return True

if add_approver(driver, "강동휘") and add_approver(driver, "김경영"):
    # 3-3) 결재선 지정 저장
    print("\n3. 결재선 저장...")
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
    time.sleep(2.0)
    # 저장 시 컨펌 모달이 뜰 수 있음
    dismiss_confirm_alert(driver, "저장후")
else:
    sys.exit("결재자 지정 오류로 중단.")

# 4) 최종 상신 클릭
print("\n4. 최종 [상신] 버튼 클릭...")
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
time.sleep(2.0)

# 최종 확인 및 알림 창 순차 처리
print("\n5. 최종 확인 모달창 처리...")
for i in range(4):
    if dismiss_confirm_alert(driver, f"상신승인-{i+1}"):
        time.sleep(1.5)
    else:
        time.sleep(1.0)

print("\n=== [완료] 상신 복구 및 최종 결재 상신 처리가 완료되었습니다! ===")
