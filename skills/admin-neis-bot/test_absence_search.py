#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""결석신고서관리에서 3초 대기 후 조회를 눌렀을 때 데이터셋이 정상 조회되는지 확인하는 테스트 스크립트."""

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

# 1) 결석신고서관리 탭 활성화
print("1. 결석신고서관리 메뉴 검색 및 탭 전환...")
js_search = """
var inst = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "app/com/main/Index";
});
if (!inst) return {error: "Index app not found"};

var searchInput = inst.lookup("siFindMenu");
if (!searchInput) return {error: "siFindMenu not found"};

searchInput.value = "결석신고서관리";
var event = new cpr.events.CUIEvent("search");
searchInput.dispatchEvent(event);
return {ok: true};
"""
driver.execute_script(js_search)
time.sleep(2.0)

# 메뉴 클릭
js_click = """
var all = document.querySelectorAll('*');
for (var i = 0; i < all.length; i++) {
    var el = all[i];
    var text = (el.innerText || el.textContent || "").trim();
    if (text === "결석신고서관리" && (el.tagName === "SPAN" || el.tagName === "DIV" || el.tagName === "A")) {
        el.click();
        return {ok: true};
    }
}
return {error: "menu click failed"};
"""
driver.execute_script(js_click)
print("  메뉴 클릭 완료.")
time.sleep(4.0) # 충분히 콤보박스 비동기 로딩을 기다림 (4초!)

# 2) 조회 클릭 및 데이터셋 스캔
JS_SEARCH_AND_SCAN = """
return (function() {
    var inst = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
        return ai.app && ai.app.id === "edu/sa/eds/eaa/ae/eds_eaaae03_m01";
    });
    if (!inst) return {error: "eaaae03 app not found"};
    
    // 조회 클릭
    var btnSearch = inst.lookup("btnSearch");
    if (btnSearch) btnSearch.click();
    
    return {ok: true};
})();
"""
driver.execute_script(JS_SEARCH_AND_SCAN)
time.sleep(2.0) # 조회 결과 데이터 로딩 대기

# 3) 데이터셋 덤프
JS_DUMP = """
return (function() {
    var inst = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
        return ai.app && ai.app.id === "edu/sa/eds/eaa/ae/eds_eaaae03_m01";
    });
    if (!inst) return {error: "app not found"};
    
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
print("조회 결과 리스트:")
print(json.dumps(res, ensure_ascii=False, indent=2))
