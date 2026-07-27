#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import os
import sys
import json

os.environ["no_proxy"] = "localhost,127.0.0.1"

async def find_neis_page(browser):
    for context in browser.contexts:
        for page in context.pages:
            try:
                has_cpr = await page.evaluate("typeof cpr !== 'undefined'")
                url = page.url
                if has_cpr and "vpn" not in url.lower():
                    title = await page.title()
                    print(f"[window] NEIS 페이지 확보: {title}")
                    return page
            except Exception:
                pass
    raise RuntimeError("NEIS 페이지를 찾을 수 없습니다.")

async def main():
    from playwright.async_api import async_playwright
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9222")
    
    page = await find_neis_page(browser)
    
    # 1) 신청 버튼 클릭
    js_click = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var mainApp = apps.find(function(ai) { return ai.app && ai.app.id === "edu/ga/srv/mym/mm/srv_mymmm00_m00"; });
        if (!mainApp) return {error: "main app not found"};
        var btn = mainApp.lookup("btnAply");
        if (btn) { btn.click(); return {ok: true}; }
        return {error: "btnAply not found"};
    })();
    """
    res = await page.evaluate(js_click)
    print("CLICK APPLY:", res)
    await asyncio.sleep(3.0)
    
    # 2) 팝업 덤프
    js_dump = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        return apps.map(function(ai, idx) {
            var appId = ai.app ? ai.app.id : "";
            var ctrls = [];
            try {
                ai.getContainer().getAllRecursiveChildren().forEach(function(c) {
                    var items = [];
                    if (c.getItems) {
                        try {
                            items = c.getItems().map(function(it) { return {label: it.label||it.text, value: it.value}; });
                        } catch(e) {}
                    }
                    ctrls.push({
                        id: c.id || "",
                        type: c.type || "",
                        text: (c.value || c.text || c.fieldLabel || "").toString().substring(0, 80),
                        items: items.slice(0, 20)
                    });
                });
            } catch(e) {}
            return {idx: idx, appId: appId, ctrls: ctrls};
        });
    })();
    """
    dump = await page.evaluate(js_dump)
    with open("skills/admin-neis-bot/popup_dump.json", "w", encoding="utf-8") as f:
        json.dump(dump, f, ensure_ascii=False, indent=2)
        
    print("\n================== POPUP DUMP ==================")
    for app in dump:
        if app["appId"] != "app/com/main/Index" and app["appId"] != "edu/ga/srv/mym/mm/srv_mymmm00_m00":
            print(f"\nPOPUP APP: {app['appId']}")
            for c in app["ctrls"]:
                print(f"  [{c['type']:15}] id={c['id']:25} text=\"{c['text']}\"")
                if c["items"]:
                    print(f"      ITEMS:")
                    for it in c["items"]:
                        print(f"        - {it['value']}: {it['label']}")
                    
    await pw.stop()

if __name__ == "__main__":
    asyncio.run(main())
