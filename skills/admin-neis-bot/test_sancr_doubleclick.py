#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""그리드 행 더블클릭 및 강동휘 추가 테스트 스크립트."""

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

# 1) [결재자지정] 클릭해서 팝업 열기
click_pop_js = """
var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
var drftApp = instances.find(function(ai) {
    return ai && ai.app && ai.app.id === "edu/cm/wam/woa/pm/wam_woapm07_p00";
});
if (!drftApp) return {error: "drftApp not found"};
var btn = drftApp.lookup("btnSelectSancr");
if (btn) { btn.click(); return {ok: true}; }
return {error: "btn not found"};
"""
print("결재자지정 팝업 열기:", driver.execute_script(click_pop_js))
time.sleep(3.0)

# 2) '강동휘' 검색 실행
search_js = """
var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
var pop = instances.find(function(ai) {
    return ai && ai.app && ai.app.id === "edu/cm/wam/woa/pm/wam_woapm07_p04";
});
if (!pop) return {error: "p04 not open"};
var userNmInput = pop.lookup("userNm");
var btnSearch = pop.lookup("btnSearch");
if (!userNmInput || !btnSearch) return {error: "controls not found"};

userNmInput.value = "강동휘";
btnSearch.click();
return {ok: true};
"""
print("강동휘 검색:", driver.execute_script(search_js))
time.sleep(1.5)

# 3) 강동휘 행 DOM 요소를 더블클릭하고 추가 버튼 클릭
JS_DBLCLICK_AND_ADD = """
return (function() {
    var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var pop = instances.find(function(ai) {
        return ai && ai.app && ai.app.id === "edu/cm/wam/woa/pm/wam_woapm07_p04";
    });
    if (!pop) return {error: "p04 not open"};
    
    var dsMain = pop.lookup("dsMain");
    var grdUserListFrom = pop.lookup("grdUserListFrom");
    var btnAdd = pop.lookup("btn1");
    if (!dsMain || !grdUserListFrom || !btnAdd) return {error: "grd/ds/btn not found"};
    
    // 강동휘 인덱스 찾기
    var targetRow = -1;
    for (var i = 0; i < dsMain.getRowCount(); i++) {
        if (dsMain.getValue(i, "userNm") === "강동휘") {
            targetRow = i;
            break;
        }
    }
    if (targetRow === -1) return {error: "강동휘 not found in dsMain"};
    
    // 행 선택
    grdUserListFrom.selectRows([targetRow]);
    
    // DOM 찾기 및 더블클릭 이벤트 발생
    var gridEl = document.getElementById("uuid-" + grdUserListFrom.uuid);
    if (!gridEl) return {error: "grid DOM element not found"};
    
    var rowEl = gridEl.querySelector('[data-rowindex="' + targetRow + '"]');
    if (!rowEl) return {error: "row DOM element not found"};
    
    // 1. 행 클릭 포커스
    var cell = rowEl.querySelector('.cl-grid-cell, td');
    if (cell) cell.click();
    
    // 2. 더블클릭 시뮬레이션
    var dblEvent = new MouseEvent('dblclick', {
        bubbles: true,
        cancelable: true,
        view: window
    });
    rowEl.dispatchEvent(dblEvent);
    
    // 3. 추가 버튼 클릭
    btnAdd.click();
    
    // 결재자 목록 dsParam에 강동휘가 성공적으로 추가되었는지 체크
    var dsParam = pop.lookup("dsParam");
    var count = dsParam ? dsParam.getRowCount() : -1;
    var approvers = [];
    if (dsParam) {
        for (var k = 0; k < dsParam.getRowCount(); k++) {
            approvers.push(dsParam.getValue(k, "userNm"));
        }
    }
    
    return {ok: true, dsParamCount: count, approvers: approvers};
})();
"""

res_add = driver.execute_script(JS_DBLCLICK_AND_ADD)
print("강동휘 추가 결과:", res_add)
