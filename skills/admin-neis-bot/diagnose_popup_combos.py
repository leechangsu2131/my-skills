#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""현재 켜져 있는 결석신고서 상세 팝업의 콤보박스 및 컨트롤 구조를 실시간 덤프하는 스크립트."""

import io, sys
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

JS_DUMP_CONTROLS = """
var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
var pop = instances.find(function(ai) {
    return ai && ai.app && ai.app.id === "edu/sa/eds/eaa/ae/eds_eaaae03_p01";
});
if (!pop) return {error: "p01 app instance not found"};

var ctrls = [];
pop.getContainer().getAllRecursiveChildren().forEach(function(c) {
    ctrls.push({
        id: c.id || "",
        type: c.type || "",
        value: c.value || "",
        text: c.text || "",
        fieldLabel: c.fieldLabel || ""
    });
});
return ctrls;
"""

res = driver.execute_script(JS_DUMP_CONTROLS)
if isinstance(res, dict) and "error" in res:
    print("에러:", res["error"])
else:
    print(f"발견된 컨트롤 수: {len(res)}")
    for c in res:
        # combobox 또는 selection 관련 컨트롤 집중 분석
        if "combo" in c["type"] or "select" in c["type"] or "list" in c["type"] or c["id"] or c["fieldLabel"]:
            print(f"  - ID: '{c['id']}' | Type: '{c['type']}' | Label: '{c['fieldLabel']}' | Val: '{c['value']}' | Text: '{c['text']}'")
