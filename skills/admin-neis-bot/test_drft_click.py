#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import os

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
    
    # 기안 팝업(wam_woapm07_p00) 내 상신 버튼들의 클릭 가능 여부 및 텍스트 검사
    js_check_drft_btns = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var drftApp = apps.find(function(ai) { return ai && ai.app && ai.app.id.indexOf("wam_woapm07_p00") >= 0; });
        if (!drftApp) return {error: "drftApp (wam_woapm07_p00) not open"};
        
        var btns = [];
        drftApp.getContainer().getAllRecursiveChildren().forEach(function(c) {
            if (c.type === "button" || (c.id && c.id.indexOf("Drft") >= 0)) {
                btns.push({
                    id: c.id,
                    enabled: c.enabled,
                    visible: c.visible,
                    text: c.value || c.text || ""
                });
            }
        });
        return {appId: drftApp.app.id, btns: btns};
    })();
    """
    res = await page.evaluate(js_check_drft_btns)
    print("\n================ [기안 팝업 내 상신 버튼 검사] ================")
    print("RES:", res)
    await pw.stop()

if __name__ == "__main__":
    asyncio.run(main())
