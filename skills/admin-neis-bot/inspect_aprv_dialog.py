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
    
    # [승인요청] 버튼 클릭 후 뜨는 알림창 전수 조사
    js_inspect_modals = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var modals = [];
        apps.forEach(function(ai) {
            if (!ai || !ai.app) return;
            var aid = ai.app.id || "";
            var ctrls = [];
            try {
                ai.getContainer().getAllRecursiveChildren().forEach(function(c) {
                    ctrls.push({
                        id: c.id || "",
                        type: c.type || "",
                        value: (c.value || c.text || c.fieldLabel || "").toString().trim()
                    });
                });
            } catch(e) {}
            modals.push({appId: aid, ctrls: ctrls});
        });
        return modals;
    })();
    """
    res = await page.evaluate(js_inspect_modals)
    print("\n================ [모든 팝업/모달 인스턴스 전수 스캔] ================")
    for m in res:
        if "main" not in m['appId'] and "Dashboard" not in m['appId']:
            print(f"APP ID: {m['appId']}")
            for c in m['ctrls']:
                if c['value'] or c['id']:
                    safe_v = c['value'].encode('ascii', 'backslashreplace').decode()
                    print(f"   - id={c['id']:20} type={c['type']:15} val=\"{safe_v}\"")
                    
    await pw.stop()

if __name__ == "__main__":
    asyncio.run(main())
