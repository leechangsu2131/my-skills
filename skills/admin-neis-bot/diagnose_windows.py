#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""윈도우 핸들 진단을 최속으로 수행하는 스크립트."""

import sys, json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

opts = Options()
opts.add_experimental_option("debuggerAddress", "localhost:9222")

# 스피드 최적화: chromedriver binary 캐시 검색 최속화
driver = webdriver.Chrome(options=opts)

handles = driver.window_handles
print(f"WINDOW_COUNT:{len(handles)}")

results = []
for idx, h in enumerate(handles):
    try:
        driver.switch_to.window(h)
        title = driver.title
        url = driver.current_url
        has_cpr = driver.execute_script("return typeof cpr !== 'undefined';")
        results.append({
            "idx": idx,
            "handle": h,
            "title": title,
            "url": url,
            "has_cpr": has_cpr
        })
    except Exception as e:
        results.append({"idx": idx, "handle": h, "error": str(e)})

print("DUMP:" + json.dumps(results, ensure_ascii=False))
driver.quit()
