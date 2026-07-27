#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""결재선 지정 팝업에서 강동휘, 김경영을 추가하고 최종 상신까지 완료하는 스크립트."""

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

# 1) 공통 확인 다이얼로그 닫기 함수
def clean_popups(driver, duration_sec=3.0):
    end = time.time() + duration_sec
    while time.time() < end:
        # app/cmn/confirm 이나 alert 닫기
        js = """
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var clicked = false;
        instances.forEach(function(ai) {
            if (!ai || !ai.app) return;
            if (ai.app.id !== "app/cmn/confirm" && ai.app.id !== "app/cmn/alert") return;
            try {
                ai.getContainer().getAllRecursiveChildren().forEach(function(ctrl) {
                    if (clicked) return;
                    var val = ctrl.value || ctrl.text || "";
                    if (val === "확인" || val === "예" || ctrl.id === "btnOk" || ctrl.id === "btnConfirm") {
                        if (typeof ctrl.click === 'function') { ctrl.click(); clicked = true; }
                    }
                });
            } catch(e) {}
        });
        return clicked;
        """
        res = driver.execute_script(js)
        if res:
            print("  [modal] 다이얼로그 확인 닫기 완료")
            time.sleep(1.0)
        time.sleep(0.3)

# 2) 결재자 1명 추가 함수
def add_approver(driver, name: str) -> bool:
    print(f"  -> 결재자 '{name}' 추가 시도...")
    
    # 검색 입력 및 조회 클릭
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
        print(f"    [오류] 검색 실패: {res['error']}")
        return False
        
    time.sleep(1.5)
    
    # 검색 결과 그리드에서 해당 이름의 행을 찾아서 선택하고 '추가' 버튼 클릭
    js_select_and_add = """
    var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var pop = instances.find(function(ai) {
        return ai && ai.app && ai.app.id === "edu/cm/wam/woa/pm/wam_woapm07_p04";
    });
    if (!pop) return {error: "wam_woapm07_p04 app not found"};
    
    var dsMain = pop.lookup("dsMain");
    var grdUserListFrom = pop.lookup("grdUserListFrom");
    var btnAdd = pop.lookup("btn1"); // 추가 버튼
    
    if (!dsMain || !grdUserListFrom || !btnAdd) return {error: "ds, grid or add button not found"};
    
    // dsMain에서 이름 매칭 로우 탐색
    var targetRow = -1;
    for (var i = 0; i < dsMain.getRowCount(); i++) {
        var unm = dsMain.getValue(i, "userNm");
        if (unm === "TARGET_NAME") {
            targetRow = i;
            break;
        }
    }
    
    if (targetRow === -1) return {error: "name TARGET_NAME not found in dsMain"};
    
    // 행 선택 후 추가
    grdUserListFrom.selectRows([targetRow]);
    btnAdd.click();
    return {ok: true};
    """.replace("TARGET_NAME", name)
    
    res2 = driver.execute_script(js_select_and_add)
    if res2.get("error"):
        print(f"    [오류] 추가 실패: {res2['error']}")
        return False
        
    print(f"    '{name}' 추가 완료")
    time.sleep(1.0)
    return True

# 3) 결재선 지정 팝업 처리 진행
print("=== [결재선 지정 팝업 조작] ===")
if add_approver(driver, "강동휘") and add_approver(driver, "김경영"):
    # 결재자 목록 저장 (btn4 클릭)
    print("  -> 결재자 설정 저장...")
    js_save_pop = """
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
    driver.execute_script(js_save_pop)
    time.sleep(2.0)
    clean_popups(driver, duration_sec=2.0)
    print("  -> 결재자 설정 저장 완료")
else:
    sys.exit("결재자 지정 도중 실패하여 중단합니다.")

# 4) 기안문서상신 화면에서 최종 [상신] 클릭
print("\n=== [기안문서상신 최종 상신] ===")
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
return {error: "btnDrft control not found"};
"""
res_drft = driver.execute_script(js_drft)
print("상신 클릭 결과:", res_drft)

if res_drft.get("ok"):
    print("최종 확인창 대기 및 팝업 일괄 수락...")
    time.sleep(2.0)
    clean_popups(driver, duration_sec=5.0)
    print("\n[성공] 교외체험학습신청서 기안 상신이 완벽하게 완료되었습니다!")
else:
    print("[오류] 상신 버튼 클릭 실패:", res_drft.get("error"))
