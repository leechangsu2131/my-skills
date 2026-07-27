#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""결석기간 시작일을 이전 일자로 변경 후 조회를 실행하여 김주안이 검색되는지 검증하는 스크립트."""

import io, sys, time, json
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

JS_DATE_CHANGE_AND_SEARCH = """
return (function() {
    var inst = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
        return ai.app && ai.app.id === "edu/sa/eds/eaa/ae/eds_eaaae03_m01";
    });
    if (!inst) return {error: "app not found"};
    
    // 시작일(dtAbeBgngYmd) 값을 20260501로 세팅
    var dtInput = inst.lookup("dtAbeBgngYmd");
    if (!dtInput) return {error: "dtAbeBgngYmd not found"};
    
    dtInput.value = "20260501";
    
    // 조회 클릭
    var btnSearch = inst.lookup("btnSearch");
    if (btnSearch) btnSearch.click();
    
    return {ok: true};
})();
"""

print("결석시작일 변경 및 조회 시도:", driver.execute_script(JS_DATE_CHANGE_AND_SEARCH))
time.sleep(2.0)

# 결과 덤프
JS_DUMP = """
return (function() {
    var inst = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
        return ai.app && ai.app.id === "edu/sa/eds/eaa/ae/eds_eaaae03_m01";
    });
    if (!inst) return [];
    
    var ds = inst.lookup("dsStdntListForAbe");
    var list = [];
    for (var i = 0; i < ds.getRowCount(); i++) {
        list.push({
            name: ds.getValue(i, "stuFlnm"),
            status: ds.getValue(i, "eduActPrcsStsNm"),
            atrz: ds.getValue(i, "atrzStsNm")
        });
    }
    return list;
})();
"""
res = driver.execute_script(JS_DUMP)
print("조회 결과:")
print(json.dumps(res, ensure_ascii=False, indent=2))
