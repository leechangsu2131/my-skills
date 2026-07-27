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
                
    print("  -> 4차 연수 (Sn 752) 회수 시도...")
    js_recall_752 = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var mainApp = apps.find(function(ai) { return ai.app && ai.app.id === "edu/ga/srv/mym/mm/srv_mymmm00_m00"; });
        if (!mainApp) return {error: "mainApp not found"};
        
        var ds = mainApp.lookup("dsWorkSittn") || mainApp.lookup("dsMain") || mainApp.lookup("dsList");
        var grid = mainApp.lookup("grdWorkSittn") || mainApp.lookup("grdMain") || mainApp.lookup("grdList");
        if (!ds || !grid) return {error: "ds/grid not found"};
        
        var targetRow = -1;
        for (var i = 0; i < ds.getRowCount(); i++) {
            if (ds.getValue(i, "workSittnSn") === "752") {
                targetRow = i;
                break;
            }
        }
        if (targetRow < 0) return {ok: true, msg: "752건이 이미 회수되었습니다"};
        
        if (grid.clearAllCheck) grid.clearAllCheck();
        grid.setCheckRowIndex(targetRow, true);
        grid.selectRows([targetRow]);
        
        var btnRtrvl = mainApp.lookup("btnRtrvl");
        if (btnRtrvl) { btnRtrvl.click(); return {ok: true, targetRow: targetRow}; }
        return {error: "btnRtrvl not found"};
    })();
    """
    res = await page.evaluate(js_recall_752)
    print("  [OK] Sn 752 회수 클릭 결과:", res)
    await asyncio.sleep(2.0)
    
    js_dismiss = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var clicked = false;
        apps.forEach(function(ai) {
            if (!ai || !ai.app) return;
            var aid = ai.app.id || "";
            if (aid.indexOf("confirm") >= 0 || aid.indexOf("alert") >= 0 || aid.indexOf("cmn") >= 0) {
                try {
                    ai.getContainer().getAllRecursiveChildren().forEach(function(c) {
                        if (clicked) return;
                        var id = c.id || "";
                        var val = "";
                        try { val = (c.value || c.text || "").toString().trim(); } catch(e) {}
                        if (id === "btnOk" || id === "btnConfirm" || id === "btnYes" || val === "확인" || val === "예" || val === "OK") {
                            if (typeof c.click === 'function') { c.click(); clicked = true; }
                        }
                    });
                } catch(e) {}
            }
        });
        return clicked;
    })();
    """
    for k in range(3):
        c_res = await page.evaluate(js_dismiss)
        print(f"    - 모달 닫기 {k+1}회:", c_res)
        await asyncio.sleep(1.5)
        
    await pw.stop()

if __name__ == "__main__":
    asyncio.run(main())
