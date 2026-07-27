#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""이미 열려 있는 결석신고서 상세 팝업에서 질병결석 지정 후 저장, 상신을 마무리하는 완결 스크립트."""

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

# 1) 상세 팝업에서 질병결석(01) 재확인 후 [저장] 및 [닫기]
print("\n1. 결석구분 질병결석(01) 설정 및 [저장] 시도...")
js_save_detail = """
var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
var pop = instances.find(function(ai) {
    return ai && ai.app && ai.app.id === "edu/sa/eds/eaa/ae/eds_eaaae03_p01";
});
if (!pop) return {error: "p01 app not found"};

var cmb = pop.lookup("cmbAbeDclrScCd");
if (cmb) cmb.value = "01"; // 질병결석 안전 확인

var btnSave = pop.lookup("btnUpdateSave");
if (btnSave) {
    btnSave.click();
    return {ok: true};
}
return {error: "btnUpdateSave not found"};
"""
res_save = driver.execute_script(js_save_detail)
print("  결과:", res_save)
time.sleep(1.5)
dismiss_confirm_alert(driver, "p01저장확인")
time.sleep(1.5)
dismiss_confirm_alert(driver, "p01저장완료알림")

print("\n2. 상세 팝업 [닫기] 시도...")
js_close_detail = """
var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
var pop = instances.find(function(ai) {
    return ai && ai.app && ai.app.id === "edu/sa/eds/eaa/ae/eds_eaaae03_p01";
});
if (!pop) return {error: "p01 app not found"};
var btnClose = pop.lookup("btnCancel");
if (btnClose) {
    btnClose.click();
    return {ok: true};
}
return {error: "btnCancel not found"};
"""
driver.execute_script(js_close_detail)
time.sleep(2.0)

# 3) 메인화면 재조회 실행
print("\n3. 메인화면 재조회...")
js_search = """
var inst = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "edu/sa/eds/eaa/ae/eds_eaaae03_m01";
});
if (!inst) return {error: "m01 not found"};

// 시작일 20260501로 세팅 유지
var dtInput = inst.lookup("dtAbeBgngYmd");
if (dtInput) dtInput.value = "20260501";

var btnSearch = inst.lookup("btnSearch");
if (btnSearch) {
    btnSearch.click();
    return {ok: true};
}
return {error: "btnSearch not found"};
"""
driver.execute_script(js_search)
time.sleep(2.5)

# 4) 김주안(Index 0) 체크박스 직접 클릭 및 승인요청
print("\n4. 김주안(Index 0) 체크박스 클릭 및 승인요청...")
js_check_and_request = """
var inst = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "edu/sa/eds/eaa/ae/eds_eaaae03_m01";
});
if (!inst) return {error: "m01 not found"};

var grid = inst.lookup("grdMain");
var ds = inst.lookup("dsStdntListForAbe");
if (!grid || !ds) return {error: "grid/ds not found"};

// 0행 김주안 체크박스 DOM 강제 클릭
var gridEl = document.getElementById("uuid-" + grid.uuid);
if (!gridEl) return {error: "grid DOM not found"};

var rowEl = gridEl.querySelector('[data-rowindex="0"]');
if (!rowEl) return {error: "row DOM not found"};

var chkBox = rowEl.querySelector('.cl-grid-checkbox, [role="checkbox"], input[type="checkbox"], .cl-checkbox');
if (!chkBox) return {error: "checkbox element not found"};

chkBox.click();

// 승인요청 클릭
var btnRequest = inst.lookup("btnUpdateCancel3");
if (btnRequest) {
    btnRequest.click();
    return {ok: true};
}
return {error: "btnUpdateCancel3 not found"};
"""
res_req = driver.execute_script(js_check_and_request)
print("  결과:", res_req)
time.sleep(2.5)
dismiss_confirm_alert(driver, "승인요청컨펌")
time.sleep(3.0) # 기안 팝업 로딩 대기

# 5) 결재자 강동휘 -> 김경영 추가 및 저장
print("\n5. 결재선 지정 (강동휘 -> 김경영) 진행...")
js_click_select = """
var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
var drftApp = instances.find(function(ai) {
    return ai && ai.app && ai.app.id === "edu/cm/wam/woa/pm/wam_woapm07_p00";
});
if (!drftApp) return false;
var btn = drftApp.lookup("btnSelectSancr");
if (btn) { btn.click(); return true; }
return false;
"""
driver.execute_script(js_click_select)
time.sleep(3.0)

def add_sancr(name: str) -> bool:
    print(f"  -> 결재자 '{name}' 더블클릭 추가...")
    js_add = """
    var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var pop = instances.find(function(ai) {
        return ai && ai.app && ai.app.id === "edu/cm/wam/woa/pm/wam_woapm07_p04";
    });
    if (!pop) return {error: "p04 app not found"};
    
    var dsMain = pop.lookup("dsMain");
    var grdUserListFrom = pop.lookup("grdUserListFrom");
    var btnAdd = pop.lookup("btn1");
    if (!dsMain || !grdUserListFrom || !btnAdd) return {error: "ds/grid/btn not found"};
    
    var targetRow = -1;
    for (var i = 0; i < dsMain.getRowCount(); i++) {
        if (dsMain.getValue(i, "userNm") === "TARGET_NAME") {
            targetRow = i;
            break;
        }
    }
    if (targetRow === -1) return {error: "TARGET_NAME not found in dsMain"};
    
    var gridEl = document.getElementById("uuid-" + grdUserListFrom.uuid);
    var rowEl = gridEl.querySelector('[data-rowindex="' + targetRow + '"]');
    var targetSpan = null;
    var candidates = rowEl.querySelectorAll('span, div, td, a');
    for (var i = 0; i < candidates.length; i++) {
        if (candidates[i].innerText.trim() === "TARGET_NAME") {
            targetSpan = candidates[i];
            break;
        }
    }
    if (!targetSpan) return {error: "span with text TARGET_NAME not found"};
    
    targetSpan.click();
    var dblEvent = new MouseEvent('dblclick', { bubbles: true, cancelable: true, view: window });
    targetSpan.dispatchEvent(dblEvent);
    
    grdUserListFrom.selectRows([targetRow]);
    btnAdd.click();
    return {ok: true};
    """.replace("TARGET_NAME", name)
    
    r = driver.execute_script(js_add)
    if r.get("error"):
        print(f"    [오류] '{name}' 추가 실패: {r['error']}")
        return False
    print(f"    '{name}' 추가 완료")
    time.sleep(1.5)
    return True

if add_sancr("강동휘") and add_sancr("김경영"):
    # 결재선 저장 (btn4 클릭)
    print("\n6. 결재선 저장...")
    js_save = """
    var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var pop = instances.find(function(ai) {
        return ai && ai.app && ai.app.id === "edu/cm/wam/woa/pm/wam_woapm07_p04";
    });
    if (!pop) return false;
    var btnSave = pop.lookup("btn4");
    if (btnSave) { btnSave.click(); return true; }
    return false;
    """
    driver.execute_script(js_save)
    time.sleep(2.5)
    dismiss_confirm_alert(driver, "p04저장후")
    
    # 7) 최종 상신 클릭
    print("\n7. 최종 [상신] 클릭...")
    js_drft = """
    var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var drftApp = instances.find(function(ai) {
        return ai && ai.app && ai.app.id === "edu/cm/wam/woa/pm/wam_woapm07_p00";
    });
    if (!drftApp) return false;
    var btnDrft = drftApp.lookup("btnDrft");
    if (btnDrft) { btnDrft.click(); return true; }
    return false;
    """
    driver.execute_script(js_drft)
    time.sleep(3.0)
    
    # 최종 모달들 순차 수락
    print("\n8. 최종 상신 모달 수락...")
    for i in range(5):
        if dismiss_confirm_alert(driver, f"최종상신완료-{i+1}"):
            time.sleep(2.0)
        else:
            time.sleep(1.0)
            
    print("\n=== [완료] 결석신고서 접수 및 상신 최종 처리 완료! ===")
else:
    print("[오류] 결재자 추가 실패로 상신을 중단합니다.")
