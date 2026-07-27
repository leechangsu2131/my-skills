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
                
    # 그리드 checkRow / setCheckRow / selectRows API 테스트
    js_test_check = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var mainApp = apps.find(function(ai) { return ai.app && ai.app.id === "edu/ga/srv/mym/mm/srv_mymmm00_m00"; });
        if (!mainApp) return {error: "mainApp not found"};
        
        var grid = mainApp.lookup("grdWorkSittn") || mainApp.lookup("grdMain") || mainApp.lookup("grdList");
        if (!grid) return {error: "grid not found"};
        
        var methods = [];
        for (var m in grid) {
            if (typeof grid[m] === 'function' && (m.indexOf("check") >= 0 || m.indexOf("Check") >= 0 || m.indexOf("Select") >= 0 || m.indexOf("select") >= 0)) {
                methods.push(m);
            }
        }
        
        // 0번 행 체크 시도
        try { if (grid.checkRow) grid.checkRow(0, true); } catch(e) {}
        try { if (grid.setCheckRow) grid.setCheckRow(0, true); } catch(e) {}
        try { if (grid.setCheckRowState) grid.setCheckRowState(0, true); } catch(e) {}
        
        var btnRtrvl = mainApp.lookup("btnRtrvl");
        if (btnRtrvl) btnRtrvl.click();
        
        return {methods: methods};
    })();
    """
    res = await page.evaluate(js_test_check)
    print("\n================ [그리드 체크 메소드 및 회수 클릭 인스펙트] ================")
    print("RES:", res)
    await asyncio.sleep(2.0)
    
    # 뜬 모달 스캔
    js_inspect_modal = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var info = [];
        apps.forEach(function(ai) {
            if (!ai || !ai.app) return;
            var aid = ai.app.id || "";
            if (aid.indexOf("alert") >= 0 || aid.indexOf("confirm") >= 0 || aid.indexOf("cmn") >= 0) {
                var msgs = [];
                ai.getContainer().getAllRecursiveChildren().forEach(function(c) {
                    var val = (c.value || c.text || "").toString().trim();
                    if (val && val.length < 100) msgs.push(val);
                });
                info.push({aid: aid, msgs: msgs});
            }
        });
        return info;
    })();
    """
    m_info = await page.evaluate(js_inspect_modal)
    print("  [MODAL INFO]:", m_info)
    
    await pw.stop()

if __name__ == "__main__":
    asyncio.run(main())
