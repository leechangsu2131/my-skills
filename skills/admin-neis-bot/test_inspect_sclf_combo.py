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
                
    # 메인 [신청] 버튼 클릭
    js_click_apply = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var mainApp = apps.find(function(ai) { return ai.app && ai.app.id === "edu/ga/srv/mym/mm/srv_mymmm00_m00"; });
        if (!mainApp) return false;
        var btn = mainApp.lookup("btnAply");
        if (btn) { btn.click(); return true; }
        return false;
    })();
    """
    await page.evaluate(js_click_apply)
    await asyncio.sleep(2.0)
    
    # 복무 신청 팝업의 콤보박스 및 데이터셋 정밀 조사
    js_inspect_combos = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var popApp = apps.find(function(ai) {
            return ai.app && (ai.app.id.indexOf("srv_mymmm00_p00") >= 0 || ai.app.id.indexOf("srv_mymmm00_p") >= 0) && ai.app.id !== "edu/ga/srv/mym/mm/srv_mymmm00_m00";
        });
        if (!popApp) return {error: "popApp not found"};
        
        var cmbLclf = popApp.lookup("cmbWorkSittnLclfCd");
        var cmbSclf = popApp.lookup("cmbWorkSittnSclfCd");
        
        // Lclf 연수(W08) 세팅
        if (cmbLclf) {
            cmbLclf.value = "W08";
            cmbLclf.dispatchEvent(new cpr.events.CValueChangeEvent("selection-change", {oldSelection: [], newSelection: []}));
            cmbLclf.dispatchEvent(new cpr.events.CValueChangeEvent("value-change", {oldValue: "", newValue: "W08"}));
        }
        
        var sclfItems = [];
        try {
            var items = cmbSclf ? cmbSclf.getItems() : [];
            items.forEach(function(it) {
                sclfItems.push({label: it.label, value: it.value});
            });
        } catch(e) {}
        
        return {
            lclfVal: cmbLclf ? cmbLclf.value : null,
            sclfVal: cmbSclf ? cmbSclf.value : null,
            sclfItems: sclfItems
        };
    })();
    """
    res1 = await page.evaluate(js_inspect_combos)
    print("\n================ [W08 선택 직후 소분류 콤보 인스펙트] ================")
    print("RES 1:", res1)
    
    await asyncio.sleep(2.0)
    
    # 2초 후 소분류 콤보 재스캔
    res2 = await page.evaluate(js_inspect_combos)
    print("\n================ [2초 후 소분류 콤보 재스캔] ================")
    print("RES 2:", res2)
    
    await pw.stop()

if __name__ == "__main__":
    asyncio.run(main())
