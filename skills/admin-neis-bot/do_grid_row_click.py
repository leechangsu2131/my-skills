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
                
    # 그리드 0번 행 DOM 직접 클릭 및 focusCell
    print("  -> 그리드 0번 행 DOM 직접 클릭 및 회수 시도...")
    js_click_grid_row = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var mainApp = apps.find(function(ai) { return ai.app && ai.app.id === "edu/ga/srv/mym/mm/srv_mymmm00_m00"; });
        if (!mainApp) return {error: "mainApp not found"};
        
        var grid = mainApp.lookup("grdWorkSittn") || mainApp.lookup("grdMain") || mainApp.lookup("grdList");
        if (!grid) return {error: "grid not found"};
        
        grid.selectRows([0]);
        try { grid.setFocus(); } catch(e) {}
        try { if (grid.focusCell) grid.focusCell(0, 0); } catch(e) {}
        
        var el = grid.getHtmlElement ? grid.getHtmlElement() : null;
        if (el) {
            var cell = el.querySelector('.cl-grid-cell') || el.querySelector('td');
            if (cell) cell.click();
        }
        
        var btnRtrvl = mainApp.lookup("btnRtrvl");
        if (btnRtrvl) { btnRtrvl.click(); return {ok: true}; }
        return {error: "btnRtrvl not found"};
    })();
    """
    res = await page.evaluate(js_click_grid_row)
    print("  [OK] 클릭 및 회수 결과:", res)
    await asyncio.sleep(2.0)
    
    # 뜬 모달 닫기
    js_dismiss = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var clicked = false;
        var info = [];
        apps.forEach(function(ai) {
            if (!ai || !ai.app) return;
            var aid = ai.app.id || "";
            if (aid.indexOf("confirm") >= 0 || aid.indexOf("alert") >= 0 || aid.indexOf("cmn") >= 0) {
                var msgs = [];
                ai.getContainer().getAllRecursiveChildren().forEach(function(c) {
                    var val = (c.value || c.text || "").toString().trim();
                    if (val && val.length < 100) msgs.push(val);
                    if (c.id === "btnOk" || c.id === "btnConfirm" || c.id === "btnYes" || val === "확인" || val === "예" || val === "OK") {
                        if (typeof c.click === 'function') { c.click(); clicked = true; }
                    }
                });
                info.push({aid: aid, msgs: msgs});
            }
        });
        return {clicked: clicked, info: info};
    })();
    """
    for i in range(3):
        d_res = await page.evaluate(js_dismiss)
        print(f"    - 모달 닫기 {i+1}회:", d_res)
        await asyncio.sleep(1.5)
        
    await pw.stop()

if __name__ == "__main__":
    asyncio.run(main())
