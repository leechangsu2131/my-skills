#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DOM 텍스트 매칭으로 팝업을 강제 닫고, 메인 화면 조회를 완전히 기다린 뒤 다시 일괄등록 팝업을 띄우는 완전 조치 스크립트."""

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

JS_FORCE_CLOSE_AND_REQUERY = """
// 1. DOM에서 '닫기' 버튼 찾아서 클릭
var all = document.querySelectorAll('*');
var closed = false;
for (var i = 0; i < all.length; i++) {
    var el = all[i];
    var text = (el.innerText || el.textContent || "").trim();
    if (text === "닫기" && (el.tagName === "SPAN" || el.tagName === "DIV" || el.tagName === "BUTTON")) {
        // 부모 cl-button이나 BUTTON이 있으면 거기로
        var target = el;
        for (var d=0; d<5; d++) {
            if (target.classList && (target.classList.contains("cl-button") || target.tagName === "BUTTON")) {
                break;
            }
            if (target.parentElement) target = target.parentElement;
            else break;
        }
        target.click();
        closed = true;
        break;
    }
}

// 2. 메인 앱 찾기
var main = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce01_m07";
});
if (!main) return {error: "els_sdlce01_m07 not found", closed: closed};

// 3. 조회 클릭
var btnSearch = main.lookup("btnSearch");
if (btnSearch) {
    btnSearch.click();
    return {ok: true, closed: closed, step: "search_clicked"};
}
return {error: "btnSearch not found", closed: closed};
"""

print("[run] 팝업 강제 닫기 및 메인 조회 클릭...")
res_close = driver.execute_script(JS_FORCE_CLOSE_AND_REQUERY)
print("  결과:", res_close)

# 메인 조회 로딩 충분히 대기 (7초)
print("조회 로딩 완료 대기 중 (7초)...")
time.sleep(7.0)

JS_TRIGGER_BATCH = """
var main = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce01_m07";
});
if (!main) return {error: "els_sdlce01_m07 not found"};

// 메인 그리드 행수 체크
var dsGicRec = main.lookup("dsGicRec");
var mainRows = dsGicRec ? dsGicRec.getRowCount() : 0;

var btnBnde = main.lookup("btnBndeSave"); // 일괄등록
if (btnBnde) {
    btnBnde.click();
    return {ok: true, mainRows: mainRows};
}
return {error: "btnBndeSave not found on main"};
"""

print("[run] 일괄등록 버튼 재클릭...")
res_reopen = driver.execute_script(JS_TRIGGER_BATCH)
print("  결과:", res_reopen)

# 팝업 로드 대기 (4.5초)
time.sleep(4.5)

# 신규 팝업 상태 캡처
driver.save_screenshot("scratch/screenshot.png")
print("스크린샷 갱신 완료.")
