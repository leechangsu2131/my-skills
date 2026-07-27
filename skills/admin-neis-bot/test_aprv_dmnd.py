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
    
    # 1) 승인요청(btnAprvDmnd) 버튼 클릭
    js_click_aprv = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var popApp = apps.find(function(ai) {
            return ai.app && (ai.app.id.indexOf("srv_mymmm00_p") >= 0 || ai.app.id.indexOf("srv_mymmm00") >= 0) && ai.app.id !== "edu/ga/srv/mym/mm/srv_mymmm00_m00";
        });
        if (!popApp) return {error: "popApp not found"};
        var btn = popApp.lookup("btnAprvDmnd");
        if (btn) { btn.click(); return {ok: true}; }
        return {error: "btnAprvDmnd not found"};
    })();
    """
    res = await page.evaluate(js_click_aprv)
    print("CLICK APRV RES:", res)
    await asyncio.sleep(2.0)
    
    # 2) 연속 다이얼로그 닫기
    js_dismiss = """
    (function() {
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var logs = [];
        instances.forEach(function(ai) {
            if (!ai || !ai.app) return;
            var aid = ai.app.id || "";
            logs.push(aid);
            if (aid.indexOf("confirm") >= 0 || aid.indexOf("alert") >= 0 || aid.indexOf("cmn") >= 0) {
                try {
                    ai.getContainer().getAllRecursiveChildren().forEach(function(ctrl) {
                        var val = ctrl.value || ctrl.text || "";
                        if (val === "확인" || val === "예" || val === "OK") {
                            if (typeof ctrl.click === 'function') ctrl.click();
                        }
                    });
                } catch(e) {}
            }
        });
        return logs;
    })();
    """
    
    for i in range(5):
        logs = await page.evaluate(js_dismiss)
        print(f"DISMISS LOOP {i+1} RUNNING APPS:", logs)
        await asyncio.sleep(1.5)
        
    await pw.stop()

if __name__ == "__main__":
    asyncio.run(main())
