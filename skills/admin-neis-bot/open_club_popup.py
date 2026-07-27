#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""동아리활동관리 탭을 검색 오픈하고 일괄등록 팝업을 띄운 뒤 화면을 캡처하는 스크립트."""

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

# 1) 동아리활동관리 탭 검색 및 전환
print("1. 동아리활동관리 탭 강제 검색 및 활성화...")
js_search = """
var inst = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "app/com/main/Index";
});
if (!inst) return {error: "Index app not found"};

var searchInput = inst.lookup("siFindMenu");
if (!searchInput) return {error: "siFindMenu not found"};

searchInput.value = "동아리활동관리";
var event = new cpr.events.CUIEvent("search");
searchInput.dispatchEvent(event);
return {ok: true};
"""
driver.execute_script(js_search)
time.sleep(2.0)

js_click = """
var all = document.querySelectorAll('*');
for (var i = 0; i < all.length; i++) {
    var el = all[i];
    var text = (el.innerText || el.textContent || "").trim();
    if (text === "동아리활동관리" && (el.tagName === "SPAN" || el.tagName === "DIV" || el.tagName === "A")) {
        el.click();
        return {ok: true};
    }
}
return {error: "menu text not found"};
"""
driver.execute_script(js_click)
print("  탭 클릭 완료.")
time.sleep(4.0) # 충분한 로딩 대기

# 2) 조회 클릭 및 일괄등록 클릭
print("2. 조회 및 일괄등록 클릭...")
JS_SEARCH_AND_BATCH = """
var inst = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce01_m07";
});
if (!inst) return {error: "els_sdlce01_m07 not found"};

var btnSearch = inst.lookup("btnSearch");
if (btnSearch) btnSearch.click();

setTimeout(function() {
    var btnBnde = inst.lookup("btnBndeSave"); // 일괄등록
    if (btnBnde) btnBnde.click();
}, 1500);
return {ok: true};
"""
driver.execute_script(JS_SEARCH_AND_BATCH)
time.sleep(4.5) # 팝업 로딩 대기

# 3) 스크린샷 캡처
driver.save_screenshot("scratch/screenshot.png")
print("스크린샷 저장 성공.")
