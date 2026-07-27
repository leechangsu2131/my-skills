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
                
    js_read_alert = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var alertApp = apps.find(function(ai) { return ai.app && ai.app.id === "app/cmn/alert"; });
        if (!alertApp) return {error: "alertApp not found"};
        var texts = [];
        alertApp.getContainer().getAllRecursiveChildren().forEach(function(c) {
            var t = c.value || c.text || "";
            if (t) texts.push(t);
        });
        return {texts: texts};
    })();
    """
    res = await page.evaluate(js_read_alert)
    print("\nALERT TEXTS:", res)
    await pw.stop()

if __name__ == "__main__":
    asyncio.run(main())
