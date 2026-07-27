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
                
    js_test_w08 = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var popApp = apps.find(function(ai) {
            return ai.app && (ai.app.id.indexOf("srv_mymmm00_p00") >= 0 || ai.app.id.indexOf("srv_mymmm00_p") >= 0) && ai.app.id !== "edu/ga/srv/mym/mm/srv_mymmm00_m00";
        });
        if (!popApp) return {error: "popApp not found"};
        
        var cmbLclf = popApp.lookup("cmbWorkSittnLclfCd");
        if (cmbLclf) {
            var old = cmbLclf.value;
            cmbLclf.value = "W08";
            try { cmbLclf.redraw(); } catch(e) {}
            try {
                var evt = new cpr.events.CValueChangeEvent("selection-change", {oldValue: [old], newValue: ["W08"]});
                cmbLclf.dispatchEvent(evt);
            } catch(e) {}
            try {
                var evt2 = new cpr.events.CValueChangeEvent("value-change", {oldValue: old, newValue: "W08"});
                cmbLclf.dispatchEvent(evt2);
            } catch(e) {}
        }
        
        return {ok: true};
    })();
    """
    await page.evaluate(js_test_w08)
    await asyncio.sleep(1.5)
    
    js_inspect_sclf = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var popApp = apps.find(function(ai) {
            return ai.app && (ai.app.id.indexOf("srv_mymmm00_p00") >= 0 || ai.app.id.indexOf("srv_mymmm00_p") >= 0) && ai.app.id !== "edu/ga/srv/mym/mm/srv_mymmm00_m00";
        });
        if (!popApp) return {error: "popApp not found"};
        var cmbSclf = popApp.lookup("cmbWorkSittnSclfCd");
        if (!cmbSclf) return {error: "cmbSclf not found"};
        
        var items = [];
        if (cmbSclf.getItems) {
            cmbSclf.getItems().forEach(function(it) {
                items.push({label: it.label, value: it.value});
            });
        }
        return {selectedValue: cmbSclf.value, items: items};
    })();
    """
    res = await page.evaluate(js_inspect_sclf)
    print("\n[대분류 W08(연수) 선택 후 소분류 아이템 목록]:", res)
    await pw.stop()

if __name__ == "__main__":
    asyncio.run(main())
