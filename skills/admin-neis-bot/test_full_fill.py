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
                
    js_fill_and_click = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var popApp = apps.find(function(ai) {
            return ai.app && (ai.app.id.indexOf("srv_mymmm00_p00") >= 0 || ai.app.id.indexOf("srv_mymmm00_p") >= 0);
        });
        if (!popApp) return {error: "popApp not found"};
        
        function setVal(id, val) {
            var c = popApp.lookup(id);
            if (!c) return false;
            var old = c.value;
            c.value = val;
            try { c.redraw(); } catch(e) {}
            try {
                var evt = new cpr.events.CValueChangeEvent("value-change", {oldValue: old, newValue: val});
                c.dispatchEvent(evt);
            } catch(e) {}
            return true;
        }
        
        setVal("cmbWorkSittnSclfCd", "W0105");
        setVal("dtiWorkYmdFrom", "20260728");
        setVal("dtiWorkYmdTo", "20260731");
        setVal("cmbBgngH", "12");
        setVal("cmbBgngM", "10");
        setVal("cmbEndH", "16");
        setVal("cmbEndM", "40");
        setVal("cbxDdRpatYn", "Y");
        setVal("ipbDestiNm", "화천 자택");
        setVal("ipbWorkSittnRsnCn", "교육연극을 활용한 국어수업 연구");
        
        var btn = popApp.lookup("btnAprvDmnd");
        if (btn) { btn.click(); return {ok: true}; }
        return {error: "btnAprvDmnd not found"};
    })();
    """
    res = await page.evaluate(js_fill_and_click)
    print("FILL & CLICK RES:", res)
    await asyncio.sleep(2.0)
    
    # 생성된 앱 인스턴스 확인
    js_apps = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        return apps.map(function(ai) { return ai.app ? ai.app.id : ""; });
    })();
    """
    for i in range(5):
        await asyncio.sleep(1.0)
        apps = await page.evaluate(js_apps)
        print(f"[{i+1}s] APPS:", apps)
        
    await pw.stop()

if __name__ == "__main__":
    asyncio.run(main())
