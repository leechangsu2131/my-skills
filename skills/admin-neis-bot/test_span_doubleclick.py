#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""정확히 이름이 들어간 span 엘리먼트를 직접 더블클릭하여 결재자를 추가하는 테스트 스크립트."""

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

# 1) 이름 텍스트 엘리먼트 더블클릭 수행
JS_SPAN_DBLCLICK = """
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
    
    // 강동휘 인덱스
    var targetRow = -1;
    for (var i = 0; i < dsMain.getRowCount(); i++) {
        if (dsMain.getValue(i, "userNm") === "강동휘") {
            targetRow = i;
            break;
        }
    }
    if (targetRow === -1) return {error: "강동휘 not found in dsMain"};
    
    // 그리드 DOM
    var gridEl = document.getElementById("uuid-" + grdUserListFrom.uuid);
    if (!gridEl) return {error: "grid DOM element not found"};
    
    var rowEl = gridEl.querySelector('[data-rowindex="' + targetRow + '"]');
    if (!rowEl) return {error: "row DOM element not found"};
    
    // 텍스트가 정확히 "강동휘"인 span/div 찾기
    var targetSpan = null;
    var candidates = rowEl.querySelectorAll('span, div, td, a');
    for (var i = 0; i < candidates.length; i++) {
        if (candidates[i].innerText.trim() === "강동휘") {
            targetSpan = candidates[i];
            break;
        }
    }
    
    if (!targetSpan) return {error: "span with text 강동휘 not found"};
    
    // 더블클릭 이벤트 발생
    targetSpan.click();
    var dblEvent = new MouseEvent('dblclick', {
        bubbles: true,
        cancelable: true,
        view: window
    });
    targetSpan.dispatchEvent(dblEvent);
    
    // 혹시 모를 추가 버튼 클릭도 병행
    grdUserListFrom.selectRows([targetRow]);
    btnAdd.click();
    
    // dsParam 검증
    var dsParam = pop.lookup("dsParam");
    var list = [];
    if (dsParam) {
        for (var k = 0; k < dsParam.getRowCount(); k++) {
            list.push(dsParam.getValue(k, "userNm"));
        }
    }
    return {ok: true, list: list};
})();
"""

res = driver.execute_script(JS_SPAN_DBLCLICK)
print("강동휘 추가(더블클릭) 결과:", res)
