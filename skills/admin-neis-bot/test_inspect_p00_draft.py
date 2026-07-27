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
                
    js_inspect_drft = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var drftApp = apps.find(function(ai) { return ai && ai.app && ai.app.id.indexOf("wam_woapm07_p00") >= 0; });
        if (!drftApp) return {error: "drftApp not found"};
        
        var ctrls = [];
        drftApp.getContainer().getAllRecursiveChildren().forEach(function(c) {
            ctrls.push({
                id: c.id || "",
                type: c.type || "",
                text: (c.value || c.text || c.fieldLabel || "").toString().substring(0, 80)
            });
        });
        return {appId: drftApp.app.id, ctrls: ctrls};
    })();
    """
    res = await page.evaluate(js_inspect_drft)
    print("\n================ DRAFT P00 CONTROLS ================")
    print("APP ID:", res.get("appId"))
    for c in res.get("ctrls", []):
        if c["type"] == "button" or "btn" in c["id"].lower() or "결재" in c["text"] or "상신" in c["text"]:
            print(f"  [{c['type']:15}] id={c['id']:25} text=\"{c['text']}\"")
            
    await pw.stop()

if __name__ == "__main__":
    asyncio.run(main())
