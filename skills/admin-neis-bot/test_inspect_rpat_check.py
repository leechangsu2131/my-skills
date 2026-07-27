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
                
    # 메인 [신청] 클릭
    await page.evaluate("""
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var mainApp = apps.find(function(ai) { return ai.app && ai.app.id === "edu/ga/srv/mym/mm/srv_mymmm00_m00"; });
        if (mainApp) mainApp.lookup("btnAply").click();
    })();
    """)
    await asyncio.sleep(2.0)
    
    # cbxDdRpatYn 체크박스 속성 및 Y 설정 인스펙트
    js_test_rpat = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var popApp = apps.find(function(ai) {
            return ai.app && (ai.app.id.indexOf("srv_mymmm00_p00") >= 0 || ai.app.id.indexOf("srv_mymmm00_p") >= 0) && ai.app.id !== "edu/ga/srv/mym/mm/srv_mymmm00_m00";
        });
        if (!popApp) return {error: "popApp not found"};
        
        var cbxDd = popApp.lookup("cbxDdRpatYn");
        if (!cbxDd) return {error: "cbxDdRpatYn not found"};
        
        var beforeVal = cbxDd.value;
        var trueVal = cbxDd.trueValue;
        var falseVal = cbxDd.falseValue;
        
        // Y 값 대입 및 redraw
        cbxDd.value = "Y";
        try { cbxDd.redraw(); } catch(e) {}
        try {
            cbxDd.dispatchEvent(new cpr.events.CValueChangeEvent("value-change", {oldValue: beforeVal, newValue: "Y"}));
        } catch(e) {}
        
        return {
            beforeVal: beforeVal,
            afterVal: cbxDd.value,
            trueVal: trueVal,
            falseVal: falseVal
        };
    })();
    """
    res = await page.evaluate(js_test_rpat)
    print("\n================ [일 반복 체크박스 (cbxDdRpatYn) 속성 및 세팅 인스펙트] ================")
    print("RES:", res)
    
    # 팝업 닫기
    await page.evaluate("""
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var popApp = apps.find(function(ai) {
            return ai.app && (ai.app.id.indexOf("srv_mymmm00_p00") >= 0 || ai.app.id.indexOf("srv_mymmm00_p") >= 0) && ai.app.id !== "edu/ga/srv/mym/mm/srv_mymmm00_m00";
        });
        if (popApp && popApp.lookup("btnClose")) popApp.lookup("btnClose").click();
    })();
    """)
    
    await pw.stop()

if __name__ == "__main__":
    asyncio.run(main())
