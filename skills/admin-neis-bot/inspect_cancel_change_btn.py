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
                
    # 메인 화면 srv_mymmm00_m00 의 모든 버튼 및 툴바 인스펙트
    js_inspect_main_btns = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var mainApp = apps.find(function(ai) { return ai.app && ai.app.id === "edu/ga/srv/mym/mm/srv_mymmm00_m00"; });
        if (!mainApp) return {error: "mainApp not found"};
        
        var btns = [];
        mainApp.getContainer().getAllRecursiveChildren().forEach(function(c) {
            if (c.type === "button" || (c.id && (c.id.indexOf("btn") >= 0 || c.id.indexOf("Btn") >= 0))) {
                btns.push({
                    id: c.id,
                    enabled: c.enabled,
                    visible: c.visible,
                    text: (c.value || c.text || c.fieldLabel || "").toString().trim()
                });
            }
        });
        return {appId: mainApp.app.id, btns: btns};
    })();
    """
    res = await page.evaluate(js_inspect_main_btns)
    print("\n================ [메인 근무상황 화면 버튼 목록 점검] ================")
    print("RES:", res)
    for b in res.get("btns", []):
        safe_t = b['text'].encode('ascii', 'backslashreplace').decode()
        print(f"  - id={b['id']:25} enabled={str(b['enabled']):5} text=\"{safe_t}\"")
        
    await pw.stop()

if __name__ == "__main__":
    asyncio.run(main())
