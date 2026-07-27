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
                
    # ── 1) 복무 팝업 신청 버튼 누르기 ──
    js_aprv = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var popApp = apps.find(function(ai) {
            return ai.app && (ai.app.id.indexOf("srv_mymmm00_p00") >= 0 || ai.app.id.indexOf("srv_mymmm00_p") >= 0) && ai.app.id !== "edu/ga/srv/mym/mm/srv_mymmm00_m00";
        });
        if (!popApp) return false;
        var btnAprv = popApp.lookup("btnAprvDmnd");
        if (btnAprv) { btnAprv.click(); return true; }
        return false;
    })();
    """
    await page.evaluate(js_aprv)
    await asyncio.sleep(2.0)
    
    # ── 2) 뜬 모달 팝업 구조 정밀 인스펙트 ──
    js_inspect_modal = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var confirmApps = [];
        apps.forEach(function(ai) {
            if (!ai || !ai.app) return;
            var aid = ai.app.id || "";
            if (aid.indexOf("confirm") >= 0 || aid.indexOf("alert") >= 0 || aid.indexOf("cmn") >= 0) {
                var ctrls = [];
                ai.getContainer().getAllRecursiveChildren().forEach(function(c) {
                    ctrls.push({
                        id: c.id || "",
                        type: c.type || "",
                        text: (c.value || c.text || c.fieldLabel || "").toString().trim()
                    });
                });
                confirmApps.push({appId: aid, ctrls: ctrls});
            }
        });
        return confirmApps;
    })();
    """
    res = await page.evaluate(js_inspect_modal)
    print("\n================ [승인요청 후 뜬 CONFIRM MODAL CONTROLS] ================")
    for capp in res:
        print("MODAL APP ID:", capp['appId'])
        for c in capp['ctrls']:
            safe_t = c['text'].encode('ascii', 'backslashreplace').decode()
            print(f"  - id={c['id']:25} type={c['type']:15} text=\"{safe_t}\"")
            
    await pw.stop()

if __name__ == "__main__":
    asyncio.run(main())
