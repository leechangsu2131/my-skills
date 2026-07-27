#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""현재 브라우저에 열려 있는 탭 목록 진단 스크립트."""

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

JS_DUMP_TABS = """
var tabs = [];
document.querySelectorAll('.cl-tabfolder-item, [role="tab"], .cl-tab, a, span').forEach(function(el) {
    var txt = (el.innerText || el.textContent || "").trim();
    if (txt) {
        tabs.push({tag: el.tagName, text: txt, id: el.id, class: el.className});
    }
});
return tabs;
"""

res = driver.execute_script(JS_DUMP_TABS)
print(f"발견된 탭 관련 요소 수: {len(res)}")
# 텍스트 기준 필터링해서 고유값 출력
unique_texts = sorted(list(set([t["text"] for t in res])))
for t in unique_texts:
    if len(t) < 40:
        print(f"  - '{t}'")
