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
    
    # dsMain 및 모든 데이터 컨트롤의 ddRpatYn 에 Y 설정 테스트
    js_set_rpat_perfect = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var popApp = apps.find(function(ai) {
            return ai.app && (ai.app.id.indexOf("srv_mymmm00_p00") >= 0 || ai.app.id.indexOf("srv_mymmm00_p") >= 0) && ai.app.id !== "edu/ga/srv/mym/mm/srv_mymmm00_m00";
        });
        if (!popApp) return {error: "popApp not found"};
        
        var cbxDd = popApp.lookup("cbxDdRpatYn");
        if (cbxDd) {
            cbxDd.value = "Y";
            try { cbxDd.redraw(); } catch(e) {}
            try { cbxDd.dispatchEvent(new cpr.events.CValueChangeEvent("value-change", {oldValue: "N", newValue: "Y"})); } catch(e) {}
        }
        
        var dcLogs = {};
        popApp.getAllDataControls().forEach(function(dc) {
            if (dc.setValue) {
                try { dc.setValue("ddRpatYn", "Y"); } catch(e) {}
                try { if (dc.getRowCount && dc.getRowCount() > 0) dc.setValue(0, "ddRpatYn", "Y"); } catch(e) {}
            }
            if (dc.getValue) {
                try { dcLogs[dc.id + ".ddRpatYn"] = dc.getValue("ddRpatYn"); } catch(e) {}
                try { if (dc.getRowCount && dc.getRowCount() > 0) dcLogs[dc.id + "[0].ddRpatYn"] = dc.getValue(0, "ddRpatYn"); } catch(e) {}
            }
        });
        
        return {cbxVal: cbxDd ? cbxDd.value : null, dcLogs: dcLogs};
    })();
    """
    res = await page.evaluate(js_set_rpat_perfect)
    print("\n================ [ddRpatYn = Y 정밀 바인딩 스캔] ================")
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
