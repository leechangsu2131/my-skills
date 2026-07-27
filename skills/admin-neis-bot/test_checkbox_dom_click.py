#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""그리드 행의 실제 체크박스 DOM 요소를 찾아 클릭하는 테스트 스크립트."""

import io, sys, time
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

# 1) 먼저 떠 있는 경고창(학생이 선택되지 않았습니다)을 닫습니다.
JS_DISMISS_ALERT = """
var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
var alertApp = instances.find(function(ai) {
    return ai && ai.app && ai.app.id === "app/cmn/alert";
});
if (alertApp) {
    var btn = null;
    alertApp.getContainer().getAllRecursiveChildren().forEach(function(ctrl) {
        var val = ctrl.value || ctrl.text || "";
        if (val === "확인" || ctrl.id === "btnOk" || ctrl.id === "btnConfirm") btn = ctrl;
    });
    if (btn) { btn.click(); return "alert closed"; }
}
return "no alert active";
"""
res_close = driver.execute_script(JS_DISMISS_ALERT)
print(res_close)
time.sleep(1.0)

# 2) 그리드 DOM 스캔하여 "접수 + 미상신" 행의 체크박스를 직접 DOM 클릭
JS_DOM_CHECK_CLICK = """
return (function() {
    var inst = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
        return ai.app && ai.app.id === "edu/sa/eds/eaa/ae/eds_eaaae01_m01";
    });
    if (!inst) return {error: "app not found"};
    
    var grid = inst.lookup("grdMain");
    var ds = inst.lookup("dsStdntListForAply");
    if (!grid || !ds) return {error: "grid/ds not found"};
    
    var gridEl = document.getElementById(grid.uuid) || document.querySelector('[data-uuid="' + grid.uuid + '"]');
    if (!gridEl) return {error: "grid DOM element not found"};
    
    // 행(row)을 구성하는 DOM 요소를 찾습니다.
    // eXBuilder6 그리드는 .cl-grid-row 클래스나 tr 구조를 가집니다.
    var rows = gridEl.querySelectorAll('.cl-grid-row, tr[role="row"]');
    var clickedCount = 0;
    var details = [];
    
    for (var r = 0; r < ds.getRowCount(); r++) {
        var status = ds.getValue(r, "eduActPrcsStsNm");
        var atrz = ds.getValue(r, "atrzStsNm");
        var name = ds.getValue(r, "stuFlnm");
        
        if (status === "접수" && atrz === "미상신") {
            // 해당 행(r)에 매핑되는 DOM 행 찾기
            // data-rowindex 속성이 매칭되는 요소를 우선 찾습니다.
            var rowEl = gridEl.querySelector('[data-rowindex="' + r + '"]');
            
            // 만약 index 기반 data-rowindex가 안 보인다면, tr 순서대로 시도
            if (!rowEl && rows.length > r) {
                // 헤더 tr이 0번일 수도 있으므로 보정 필요
                // 여기서는 index 매핑이 가장 확실합니다.
            }
            
            if (rowEl) {
                // 해당 행의 첫 번째 또는 두 번째 셀(체크박스)을 찾습니다.
                // 보통 .cl-grid-checkbox 클래스 또는 input[type="checkbox"] 가 존재합니다.
                var chkBox = rowEl.querySelector('.cl-grid-checkbox, input[type="checkbox"], .cl-checkbox, [role="checkbox"]');
                if (!chkBox) {
                    // 셀 전체 중 첫 번째 셀(보통 번호나 체크박스) 클릭 시도
                    var cells = rowEl.querySelectorAll('.cl-grid-cell, td');
                    if (cells.length > 0) {
                        // 보통 0번은 번호/선택 헤더
                        chkBox = cells[0];
                    }
                }
                
                if (chkBox) {
                    chkBox.click();
                    clickedCount++;
                    details.push({r: r, name: name, clicked: chkBox.className || chkBox.tagName});
                }
            }
        }
    }
    return {ok: true, clickedCount: clickedCount, details: details};
})();
"""

res_click = driver.execute_script(JS_DOM_CHECK_CLICK)
print("체크박스 클릭 결과:", res_click)
time.sleep(1.0)

# 3) 승인요청 다시 클릭 시도
if res_click.get("clickedCount", 0) > 0:
    click_req_js = r"""
    var inst = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
        return ai.app && ai.app.id === "edu/sa/eds/eaa/ae/eds_eaaae01_m01";
    });
    var btn = inst.lookup("btnUpdateCancel3"); // 승인요청
    if (btn) {
        btn.click();
        return {ok: true};
    }
    return {error: "btnUpdateCancel3 not found"};
    """
    res_req = driver.execute_script(click_req_js)
    print("승인요청 클릭 결과:", res_req)
