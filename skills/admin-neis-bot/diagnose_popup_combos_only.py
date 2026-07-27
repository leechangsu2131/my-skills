#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""팝업 내 콤보박스 타입 컨트롤만 필터링하여 출력하는 스크립트."""

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

JS_DUMP_COMBOS_ONLY = """
var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
var pop = instances.find(function(ai) {
    return ai && ai.app && ai.app.id === "edu/sa/eds/eaa/ae/eds_eaaae03_p01";
});
if (!pop) return {error: "p01 app instance not found"};

var list = [];
pop.getContainer().getAllRecursiveChildren().forEach(function(c) {
    if (c.type === "combobox" || c.type === "dropdownlist" || (c.id || "").indexOf("cmb") !== -1) {
        var items = [];
        try {
            if (c.getSelection) {
                c.getSelection().forEach(function(item) {
                    items.push({label: item.label, value: item.value});
                });
            }
        } catch(e) {}
        
        var dsItems = [];
        try {
            // 콤보박스에 바인딩된 아이템 목록 수집
            var ds = c.getItemSet ? c.getItemSet() : null;
            if (ds) {
                // eXBuilder6 콤보박스 아이템셋 목록
                c.getItems().forEach(function(item) {
                    dsItems.push({label: item.label, value: item.value});
                });
            }
        } catch(e) {}

        list.push({
            id: c.id || "",
            type: c.type || "",
            value: c.value || "",
            fieldLabel: c.fieldLabel || "",
            selectedItems: items,
            availableItems: dsItems
        });
    }
});
return list;
"""

res = driver.execute_script(JS_DUMP_COMBOS_ONLY)
print(f"발견된 콤보박스/드롭다운 관련 컨트롤:")
for c in res:
    print(f"ID: '{c['id']}' | Type: '{c['type']}' | Label: '{c['fieldLabel']}' | Val: '{c['value']}'")
    if c["selectedItems"]:
        print(f"  * 현재 선택된 값: {c['selectedItems']}")
    if c["availableItems"]:
        print(f"  * 사용 가능한 아이템 목록 (상위 10개): {c['availableItems'][:10]}")
