#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""메뉴 클릭 시뮬레이션 자동 이동 테스트."""

import io, sys, time
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

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

# 순차적으로 메뉴를 클릭하는 JS
JS_CLICK_MENU = r"""
return (function() {
    function findAndClick(text) {
        var all = document.querySelectorAll('*');
        for (var i = 0; i < all.length; i++) {
            var el = all[i];
            var val = (el.innerText || el.textContent || "").trim();
            // 정확히 매칭되거나 유니크한 경우
            if (val === text && (el.tagName === "SPAN" || el.tagName === "DIV" || el.tagName === "A" || el.tagName === "TD")) {
                el.click();
                return {ok: true, text: text, tagName: el.tagName, id: el.id};
            }
        }
        // 부분 매칭 시도
        for (var i = 0; i < all.length; i++) {
            var el = all[i];
            var val = (el.innerText || el.textContent || "").trim();
            if (val.indexOf(text) >= 0 && (el.tagName === "SPAN" || el.tagName === "DIV" || el.tagName === "A")) {
                // 자식이 너무 많지 않은 단말 노드 위주로 클릭
                if (el.children.length <= 1) {
                    el.click();
                    return {ok: true, text: text, partial: true, tagName: el.tagName, id: el.id};
                }
            }
        }
        return {error: text + " not found"};
    }
    
    // 이 스크립트에서는 단계별로 실행 상태를 저장하거나 동기식으로 짧은 갭을 두고 누릅니다.
    // 여기서는 우선 "학급담임"을 눌러보고 상태를 리턴합니다.
    return findAndClick("학급담임");
})();
"""

res = driver.execute_script(JS_CLICK_MENU)
print("학급담임 클릭 시도 결과:", res)
