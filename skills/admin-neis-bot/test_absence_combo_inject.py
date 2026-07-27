#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""결석신고구분 콤보박스에 질병결석(01) 값을 직접 주입하고 스크린샷으로 확인하는 스크립트."""

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

JS_INJECT_COMBO = """
return (function() {
    var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var pop = instances.find(function(ai) {
        return ai && ai.app && ai.app.id === "edu/sa/eds/eaa/ae/eds_eaaae03_p01";
    });
    if (!pop) return {error: "p01 app instance not found"};
    
    var cmb = pop.lookup("cmbAbeDclrScCd");
    if (!cmb) return {error: "cmbAbeDclrScCd not found"};
    
    // 값 주입 시도
    cmb.value = "01"; // 질병결석
    try { cmb.redraw(); } catch(e) {}
    
    // 현재 선택 라벨 확인
    var selText = "";
    try {
        if (cmb.getSelection) {
            cmb.getSelection().forEach(function(item) {
                selText = item.label;
            });
        }
    } catch(e) {}
    
    return {ok: true, value: cmb.value, selText: selText};
})();
"""

print("결석구분 값 주입 결과:", driver.execute_script(JS_INJECT_COMBO))
time.sleep(2.0)

# 스크린샷 캡처
driver.save_screenshot("scratch/screenshot.png")
print("스크린샷 갱신 완료.")
