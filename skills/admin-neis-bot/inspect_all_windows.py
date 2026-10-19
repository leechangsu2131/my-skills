#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

os.environ["no_proxy"] = "localhost,127.0.0.1"

opts = Options()
opts.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
driver = webdriver.Chrome(options=opts)

print(f"Total window handles: {len(driver.window_handles)}")

for i, h in enumerate(driver.window_handles):
    driver.switch_to.window(h)
    title = driver.title
    url = driver.current_url
    print(f"\n--- Handle [{i}] {title} ({url}) ---")
    
    js = """
    var platform = window.cpr && cpr.core && cpr.core.Platform && cpr.core.Platform.INSTANCE;
    if (!platform) return {cpr: false};
    var apps = platform.getAllRunningAppInstances();
    return {
        cpr: true,
        apps: apps.map(function(a) { return a.app ? a.app.id : 'unknown'; })
    };
    """
    try:
        res = driver.execute_script(js)
        print(f"CPR result: {res}")
    except Exception as e:
        print(f"Error checking CPR: {e}")
