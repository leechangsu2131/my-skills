#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""원격 크롬의 모든 창 핸들과 타이틀을 덤프하여 나이스 창을 검증하는 스크립트."""

import io, sys, time, json
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

opts = Options()
opts.add_experimental_option("debuggerAddress", "localhost:9222")
driver = webdriver.Chrome(options=opts)

print(f"[connect] active handles count: {len(driver.window_handles)}")

windows = []
for handle in driver.window_handles:
    try:
        driver.switch_to.window(handle)
        driver.switch_to.default_content()
        title = driver.title
        url = driver.current_url
        has_cpr = driver.execute_script("return typeof cpr !== 'undefined';")
        
        apps = []
        if has_cpr:
            apps = driver.execute_script(r"""
            var list = [];
            cpr.core.Platform.INSTANCE.getAllRunningAppInstances().forEach(function(ai) {
                list.push(ai.app ? ai.app.id : "none");
            });
            return list;
            """)
            
        windows.append({
            "handle": handle,
            "title": title,
            "url": url,
            "has_cpr": has_cpr,
            "apps": apps
        })
    except Exception as e:
        windows.append({
            "handle": handle,
            "error": str(e)
        })

print(json.dumps(windows, ensure_ascii=False, indent=2))
