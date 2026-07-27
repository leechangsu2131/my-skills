#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""브라우저 내 모든 iframe들을 순회하며 '일자추가(직접입력)' 버튼의 DOM 경로를 추적하는 디버깅 스크립트."""

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

# 1) iframe 리스트 스캔 및 iframe 전환하여 텍스트 찾기
iframes = driver.find_elements(by="xpath", value="//iframe")
print(f"발견된 iframe 개수: {len(iframes)}")

target_iframe_idx = -1
for idx, iframe in enumerate(iframes):
    try:
        driver.switch_to.frame(iframe)
        # iframe 내부에서 '일자추가'를 포함하는 텍스트가 있는지 체크
        js_find = """
        var all = document.querySelectorAll('*');
        for (var i = 0; i < all.length; i++) {
            var el = all[i];
            var text = (el.innerText || el.textContent || "").trim();
            if (text.indexOf("일자추가") !== -1 && (el.tagName === "SPAN" || el.tagName === "DIV" || el.tagName === "BUTTON")) {
                return {ok: true, text: text, tag: el.tagName, id: el.id, className: el.className};
            }
        }
        return {error: "not found"};
        """
        res = driver.execute_script(js_find)
        print(f"  - iframe[{idx}]: {res}")
        if res.get("ok"):
            target_iframe_idx = idx
            
            # 여기서 즉시 클릭도 시도!
            js_click = """
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
            if (found) {
                var clickTarget = found;
                for (var depth = 0; depth < 5; depth++) {
                    if (clickTarget.classList && (clickTarget.classList.contains("cl-button") || clickTarget.tagName === "BUTTON")) {
                        break;
                    }
                    if (clickTarget.parentElement) clickTarget = clickTarget.parentElement;
                    else break;
                }
                clickTarget.click();
                return {ok: true, clicked: clickTarget.id};
            }
            return {error: "not found text exact match"};
            """
            click_res = driver.execute_script(js_click)
            print(f"    -> 클릭 결과: {click_res}")
            
    except Exception as e:
        print(f"  - iframe[{idx}] 에러: {str(e)}")
    finally:
        driver.switch_to.default_content()

print(f"최종 매칭된 iframe 인덱스: {target_iframe_idx}")

# 클릭 후 변화 확인을 위해 대기 및 캡처
time.sleep(3.0)
driver.save_screenshot("scratch/screenshot.png")
print("스크린샷 갱신 성공.")
