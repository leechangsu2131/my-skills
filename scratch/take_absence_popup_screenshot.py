#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""결석신고서 상세 팝업을 열어둔 채 스크린샷을 찍어 화면을 분석하는 스크립트."""

import io, sys, time
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

# 1) 결석신고서관리 진입 및 김주안 클릭
JS_OPEN_JUAN = """
var inst = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "edu/sa/eds/eaa/ae/eds_eaaae03_m01";
});
if (!inst) return {error: "m01 not found"};

// 결석기간 20260501로 세팅 후 조회
var dtInput = inst.lookup("dtAbeBgngYmd");
if (dtInput) dtInput.value = "20260501";

var btnSearch = inst.lookup("btnSearch");
if (btnSearch) btnSearch.click();

// 1.5초 대기 후 김주안 행 클릭
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

driver.execute_script(JS_OPEN_JUAN)
time.sleep(4.5) # 조회 및 팝업 열리는 시간 대기

# 2) 스크린샷 저장
driver.save_screenshot("scratch/screenshot.png")
print("스크린샷 저장 성공.")
