#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""결석신고구분 콤보박스 아이템셋의 실제 코드값들을 덤프하는 스크립트."""

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

JS_DUMP_ITEMSET = """
var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
var pop = instances.find(function(ai) {
    return ai && ai.app && ai.app.id === "edu/sa/eds/eaa/ae/eds_eaaae03_p01";
});
if (!pop) return {error: "p01 app instance not found"};

var cmb = pop.lookup("cmbAbeDclrScCd");
if (!cmb) return {error: "cmbAbeDclrScCd not found"};

var items = [];
// UDC/콤보박스의 데이터셋 바인딩 룩업
var ds = cmb.getItemSet ? cmb.getItemSet() : null;
if (ds) {
    for (var i = 0; i < ds.getRowCount(); i++) {
        items.push({
            label: ds.getValue(i, cmb.labelColumnName || "label"),
            value: ds.getValue(i, cmb.valueColumnName || "value")
        });
    }
}
return {items: items, labelCol: cmb.labelColumnName, valCol: cmb.valueColumnName};
"""

res = driver.execute_script(JS_DUMP_ITEMSET)
print("결석신고구분 아이템 목록:")
for item in res.get("items", []):
    print(f"  - Label: '{item['label']}' | Value: '{item['value']}'")
