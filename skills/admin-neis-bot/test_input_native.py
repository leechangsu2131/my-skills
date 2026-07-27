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
                
    js_fill = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var alertApp = apps.find(function(ai) { return ai.app && ai.app.id === "app/cmn/alert"; });
        if (alertApp) {
            alertApp.getContainer().getAllRecursiveChildren().forEach(function(c) {
                if (c.id === "btnOk" || c.value === "확인" || c.text === "확인") {
                    if (typeof c.click === 'function') c.click();
                }
            });
        }
        
        var popApp = apps.find(function(ai) {
            return ai.app && (ai.app.id.indexOf("srv_mymmm00_p00") >= 0 || ai.app.id.indexOf("srv_mymmm00_p") >= 0);
        });
        if (!popApp) return {error: "popApp not found"};
        
        function setNative(id, val) {
            var c = popApp.lookup(id);
            if (!c) return false;
            c.value = val;
            try { c.redraw(); } catch(e) {}
            try {
                var el = c.getHtmlElement ? c.getHtmlElement() : null;
                if (el) {
                    var inp = (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') ? el : el.querySelector('input, textarea');
                    if (inp) {
                        inp.value = val;
                        inp.dispatchEvent(new Event('input', { bubbles: true }));
                        inp.dispatchEvent(new Event('change', { bubbles: true }));
                        inp.dispatchEvent(new Event('blur', { bubbles: true }));
                    }
                }
            } catch(e) {}
            return true;
        }
        
        setNative("ipbDestiNm", "화천 자택");
        setNative("ipbWorkSittnRsnCn", "교육연극을 활용한 국어수업 연구");
        setNative("txaWorkSittnRsnCn", "교육연극을 활용한 국어수업 연구");
        
        var btn = popApp.lookup("btnAprvDmnd");
        if (btn) { btn.click(); return {ok: true}; }
        return {error: "btnAprvDmnd not found"};
    })();
    """
    res = await page.evaluate(js_fill)
    print("NATIVE FILL RES:", res)
    await asyncio.sleep(2.0)
    
    js_check_apps = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        return apps.map(function(ai) { return ai.app ? ai.app.id : ""; });
    })();
    """
    for i in range(5):
        await asyncio.sleep(1.0)
        apps = await page.evaluate(js_check_apps)
        print(f"[{i+1}s] APPS:", apps)
        
    await pw.stop()

if __name__ == "__main__":
    asyncio.run(main())
