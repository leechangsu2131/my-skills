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
                
    # ROW 1 (Sn 741) 단독 회수
    print("  -> ROW 1 (2차 연수 Sn 741) 선택 및 [회수] 클릭...")
    js_rtrvl_single = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var mainApp = apps.find(function(ai) { return ai.app && ai.app.id === "edu/ga/srv/mym/mm/srv_mymmm00_m00"; });
        if (!mainApp) return {error: "mainApp not found"};
        
        var ds = mainApp.lookup("dsWorkSittn") || mainApp.lookup("dsMain") || mainApp.lookup("dsList");
        var grid = mainApp.lookup("grdWorkSittn") || mainApp.lookup("grdMain") || mainApp.lookup("grdList");
        if (!ds || !grid) return {error: "ds/grid not found"};
        
        grid.selectRows([0]);
        try {
            grid.dispatchEvent(new cpr.events.CSelectionChangeEvent("selection-change", {oldSelection: [], newSelection: [0]}));
            grid.dispatchEvent(new cpr.events.CGridEvent("row-select", {rowIndex: 0}));
        } catch(e) {}
        
        var btnRtrvl = mainApp.lookup("btnRtrvl");
        if (btnRtrvl) { btnRtrvl.click(); return {ok: true, sn: ds.getValue(0, "workSittnSn")}; }
        return {error: "btnRtrvl not found"};
    })();
    """
    res_rtrvl = await page.evaluate(js_rtrvl_single)
    print("  [OK] 회수 버튼 클릭 결과:", res_rtrvl)
    await asyncio.sleep(2.0)
    
    # 회수 Confirm 알림창 닫기 3회
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
        print(f"    - 회수 컨펌 다이얼로그 클릭 {i+1}회:", d_res)
        await asyncio.sleep(1.5)
        
    await pw.stop()

if __name__ == "__main__":
    asyncio.run(main())
