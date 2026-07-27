#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""팝업창 내의 '일자추가(직접입력)' HTML 요소를 DOM 단에서 직접 찾아 클릭해보고 캡처하는 동기 스크립트."""

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

JS_DOM_CLICK_ADD = """
var all = document.querySelectorAll('*');
var found = null;
for (var i = 0; i < all.length; i++) {
    var el = all[i];
    var text = (el.innerText || el.textContent || "").trim();
    if (text === "일자추가(직접입력)" && (el.tagName === "SPAN" || el.tagName === "DIV" || el.tagName === "BUTTON")) {
        found = el;
        break;
    }
}
if (!found) {
    // 부분 매칭 검색
    for (var i = 0; i < all.length; i++) {
        var el = all[i];
        var text = (el.innerText || el.textContent || "").trim();
        if (text.indexOf("일자추가") !== -1 && (el.tagName === "SPAN" || el.tagName === "DIV" || el.tagName === "BUTTON")) {
            found = el;
            break;
        }
    }
}

if (found) {
    // cl-button이나 최상위 클릭 가능 부모 요소로 거슬러 올라감
    var clickTarget = found;
    for (var depth = 0; depth < 5; depth++) {
        if (clickTarget.classList && (clickTarget.classList.contains("cl-button") || clickTarget.tagName === "BUTTON")) {
            break;
        }
        if (clickTarget.parentElement) {
            clickTarget = clickTarget.parentElement;
        } else {
            break;
        }
    }
    
    clickTarget.click();
    return {ok: true, clickedId: clickTarget.id || "no_id", clickedClass: clickTarget.className || "no_class"};
}
return {error: "일자추가(직접입력) button not found in DOM"};
"""

print("[run] 일자추가(직접입력) 버튼 DOM 클릭 시도...")
res = driver.execute_script(JS_DOM_CLICK_ADD)
print("결과:", res)

# 신규 모달 팝업 또는 그리드 변화 대기
time.sleep(4.0)

driver.save_screenshot("scratch/screenshot.png")
print("스크린샷 갱신 완료.")
