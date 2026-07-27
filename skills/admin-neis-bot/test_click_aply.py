#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import os
import json

os.environ["no_proxy"] = "localhost,127.0.0.1"

async def main():
    from playwright.async_api import async_playwright
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9222")
    
    page = None
    for context in browser.contexts:
        for p in context.pages:
            try:
                if await p.evaluate("typeof cpr !== 'undefined'") and "vpn" not in p.url.lower():
                    page = p
                    break
            except Exception:
                pass
                
    print(f"PAGE: {await page.title()}")
    
    # 1) 클릭 전 앱 인스턴스들
    js_get_apps = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        return apps.map(function(ai) { return ai.app ? ai.app.id : ""; });
    })();
    """
    before_apps = await page.evaluate(js_get_apps)
    print("BEFORE APPS:", before_apps)
    
    # 2) btnAply 클릭
    js_click = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var mainApp = apps.find(function(ai) { return ai.app && ai.app.id === "edu/ga/srv/mym/mm/srv_mymmm00_m00"; });
        if (!mainApp) return {error: "main app not found"};
        var btn = mainApp.lookup("btnAply");
        if (btn) {
            btn.click();
            return {ok: true, btnId: btn.id};
        }
        return {error: "btnAply not found"};
    })();
    """
    res = await page.evaluate(js_click)
    print("CLICK RES:", res)
    
    # 3) 5초간 1초 단위로 앱 변화 관찰
    for i in range(5):
        await asyncio.sleep(1.0)
        after_apps = await page.evaluate(js_get_apps)
        print(f"AFTER {i+1}s APPS:", after_apps)
        
    await pw.stop()

if __name__ == "__main__":
    asyncio.run(main())
