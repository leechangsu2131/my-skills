#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""중첩된 두 개의 일괄등록 팝업창을 완전히 닫아버리는 조치 스크립트."""

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

JS_CLOSE_ALL_POPUPS = """
var closedCount = 0;

// 1) 텍스트가 '닫기'인 요소를 전부 찾아서 클릭
var all = document.querySelectorAll('*');
var closeButtons = [];
for (var i = 0; i < all.length; i++) {
    var el = all[i];
    var text = (el.innerText || el.textContent || "").trim();
    if (text === "닫기" && (el.tagName === "SPAN" || el.tagName === "DIV" || el.tagName === "BUTTON")) {
        var target = el;
        for (var d=0; d<5; d++) {
            if (target.classList && (target.classList.contains("cl-button") || target.tagName === "BUTTON")) {
                break;
            }
            if (target.parentElement) target = target.parentElement;
            else break;
        }
        closeButtons.push(target);
    }
}

closeButtons.forEach(function(btn) {
    try {
        btn.click();
        closedCount++;
    } catch(e) {}
});

// 2) 다이얼로그 우측 상단 'X' 버튼 탐색 및 클릭 (cl-dialog-close 등)
var xButtons = document.querySelectorAll('.cl-dialog-close, [class*="close"], [class*="dialog"] .cl-button');
xButtons.forEach(function(btn) {
    var text = (btn.innerText || btn.textContent || "").trim();
    // 닫기 아이콘 버튼이거나 X인 경우
    if (btn.classList.contains("cl-dialog-close") || text === "X" || text === "x") {
        try {
            btn.click();
            closedCount++;
        } catch(e) {}
    }
});

return {ok: true, closedCount: closedCount};
"""

print("[run] 모든 팝업 닫기 버튼 및 X 버튼 일괄 클릭...")
res = driver.execute_script(JS_CLOSE_ALL_POPUPS)
print("결과:", res)

# 팝업이 완전히 사라질 때까지 대기
time.sleep(3.0)

driver.save_screenshot("scratch/screenshot.png")
print("스크린샷 갱신 완료.")
