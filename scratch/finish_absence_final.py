#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""결석신고서 접수상태를 '접수'로 전환하고 결석구분을 '질병결석'으로 지정하여 완벽 상신하는 통합 스크립트."""

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

def clean_popups(driver, duration_sec=4.0):
    end = time.time() + duration_sec
    while time.time() < end:
        dismissed = dismiss_confirm_alert(driver, "clean")
        time.sleep(0.5 if dismissed else 0.3)

# 1) 메인 화면에서 김주안 상세 팝업 오픈
print("\n1. 김주안 학생 상세조회 팝업 오픈 시도...")
js_open_detail = """
var inst = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "edu/sa/eds/eaa/ae/eds_eaaae03_m01";
});
if (!inst) return {error: "m01 not found"};

// 날짜 조건 확장
var dtInput = inst.lookup("dtAbeBgngYmd");
if (dtInput) dtInput.value = "20260501";

var btnSearch = inst.lookup("btnSearch");
if (btnSearch) btnSearch.click();

setTimeout(function() {
    var grid = inst.lookup("grdMain");
    var ds = inst.lookup("dsStdntListForAbe");
    if (!grid || !ds) return;
    
    var name = ds.getValue(0, "stuFlnm");
    grid.selectRows([0]);
    
    var gridEl = document.getElementById("uuid-" + grid.uuid);
    var rowEl = gridEl.querySelector('[data-rowindex="0"]');
    var targetSpan = null;
    var candidates = rowEl.querySelectorAll('span, div, td, a');
    for (var i = 0; i < candidates.length; i++) {
        if (candidates[i].innerText.trim() === name) {
            targetSpan = candidates[i];
            break;
        }
    }
    if (targetSpan) targetSpan.click();
}, 1500);
return {ok: true};
"""
driver.execute_script(js_open_detail)
time.sleep(5.0) # 충분한 로딩 대기

# 2) 스마트 콤보박스 변경 및 저장
print("\n2. 상세조회 팝업 콤보박스 값 스마트 설정 및 [저장]...")
js_modify_and_save = """
var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
var pop = instances.find(function(ai) {
    return ai && ai.app && ai.app.id === "edu/sa/eds/eaa/ae/eds_eaaae03_p01";
});
if (!pop) return {error: "p01 app instance not found"};

// 1. 접수상태 cmbEduActPrcsStsCd -> "접수" 설정
var cmbStatus = pop.lookup("cmbEduActPrcsStsCd");
if (cmbStatus) {
    var dsStatus = cmbStatus.getItemSet ? cmbStatus.getItemSet() : null;
    var valStatus = "02"; // 기본 백업값
    if (dsStatus) {
        for (var i = 0; i < dsStatus.getRowCount(); i++) {
            var lbl = dsStatus.getValue(i, cmbStatus.labelColumnName || "label");
            if (lbl === "접수") {
                valStatus = dsStatus.getValue(i, cmbStatus.valueColumnName || "value");
                break;
            }
        }
    }
    cmbStatus.value = valStatus;
}

// 2. 결석구분 cmbAbeDclrScCd -> "질병결석" 설정
var cmbAbe = pop.lookup("cmbAbeDclrScCd");
if (cmbAbe) {
    var dsAbe = cmbAbe.getItemSet ? cmbAbe.getItemSet() : null;
    var valAbe = "01"; // 기본 백업값
    if (dsAbe) {
        for (var k = 0; k < dsAbe.getRowCount(); k++) {
            var lblAbe = dsAbe.getValue(k, cmbAbe.labelColumnName || "label");
            if (lblAbe === "질병결석") {
                valAbe = dsAbe.getValue(k, cmbAbe.valueColumnName || "value");
                break;
            }
        }
    }
    cmbAbe.value = valAbe;
}

try { cmbStatus.redraw(); cmbAbe.redraw(); } catch(e) {}

// 3. 저장 클릭
var btnSave = pop.lookup("btnUpdateSave");
if (btnSave) {
    btnSave.click();
    return {ok: true, statusVal: cmbStatus.value, abeVal: cmbAbe.value};
}
return {error: "btnUpdateSave not found"};
"""
res_save = driver.execute_script(js_modify_and_save)
print("  저장 실행 결과:", res_save)
time.sleep(1.5)
clean_popups(driver, duration_sec=4.0)

# 3) 상세 팝업 닫기
print("\n3. 상세 팝업 닫기...")
js_close = """
var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
var pop = instances.find(function(ai) {
    return ai && ai.app && ai.app.id === "edu/sa/eds/eaa/ae/eds_eaaae03_p01";
});
if (!pop) return {error: "p01 not found"};
var btnCancel = pop.lookup("btnCancel");
if (btnCancel) { btnCancel.click(); return {ok:true}; }
return {error: "btnCancel not found"};
"""
driver.execute_script(js_close)
time.sleep(2.0)

# 4) 메인 조회 및 미상신 체크 상신요청
print("\n4. 메인화면 재조회 및 승인요청...")
js_search_and_request = """
var inst = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "edu/sa/eds/eaa/ae/eds_eaaae03_m01";
});
if (!inst) return {error: "m01 not found"};

// 시작일 세팅 및 조회
var dtInput = inst.lookup("dtAbeBgngYmd");
if (dtInput) dtInput.value = "20260501";
inst.lookup("btnSearch").click();

setTimeout(function() {
    var grid = inst.lookup("grdMain");
    var ds = inst.lookup("dsStdntListForAbe");
    if (!grid || !ds) return;
    
    // 0행 강제 체크박스 클릭
    var gridEl = document.getElementById("uuid-" + grid.uuid);
    var rowEl = gridEl.querySelector('[data-rowindex="0"]');
    var chkBox = rowEl.querySelector('.cl-grid-checkbox, [role="checkbox"], input[type="checkbox"], .cl-checkbox');
    if (chkBox) chkBox.click();
    
    // 승인요청
    var btnReq = inst.lookup("btnUpdateCancel3");
    if (btnReq) btnReq.click();
}, 2000);
return {ok: true};
"""
driver.execute_script(js_search_and_request)
time.sleep(4.0) # 조회 및 모달 대기
dismiss_confirm_alert(driver, "승인요청컨펌")
time.sleep(3.0) # 기안 팝업 로드 대기

# 5) 결재자 강동휘 -> 김경영 추가
print("\n5. 결재선 지정 팝업 로딩 및 결재자 지정...")
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
    print("[오류] 결재선 지정 오류로 완료할 수 없습니다.")
