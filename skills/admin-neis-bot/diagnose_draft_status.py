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
    
    # 기안 팝업(wam_woapm07_p00) 또는 메인 앱의 결재상태 및 폼 상태 정밀 검사
    js_inspect_status = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var info = [];
        apps.forEach(function(ai) {
            if (!ai || !ai.app) return;
            var aid = ai.app.id || "";
            var ctrls = [];
            try {
                ai.getContainer().getAllRecursiveChildren().forEach(function(c) {
                    var id = c.id || "";
                    var type = c.type || "";
                    var text = (c.value || c.text || c.fieldLabel || "").toString().trim();
                    if (id || text) ctrls.push({id: id, type: type, text: text.substring(0, 50)});
                });
            } catch(e) {}
            info.push({appId: aid, ctrlsCount: ctrls.length, ctrls: ctrls.slice(0, 20)});
        });
        return info;
    })();
    """
    res = await page.evaluate(js_inspect_status)
    print("\n================ [현재 나이스 화면 및 앱 인스턴스 전수 점검] ================")
    for item in res:
        print(f"\n[APP] ID: {item['appId']} (ctrlsCount: {item['ctrlsCount']})")
        for c in item['ctrls']:
            if "btn" in c['id'].lower() or "상신" in c['text'] or "결재" in c['text'] or "저장" in c['text'] or "상태" in c['text'] or "임시" in c['text']:
                safe_t = c['text'].encode('ascii', 'backslashreplace').decode()
                print(f"    - id={c['id']:25} type={c['type']:15} text=\"{safe_t}\"")
                
    await pw.stop()

if __name__ == "__main__":
    asyncio.run(main())
