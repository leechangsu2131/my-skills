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
                
    # 메인 그리드의 데이터셋 컬럼 및 체크박스 필드 정밀 조사
    js_check_cols = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var mainApp = apps.find(function(ai) { return ai.app && ai.app.id === "edu/ga/srv/mym/mm/srv_mymmm00_m00"; });
        if (!mainApp) return {error: "mainApp not found"};
        
        var ds = mainApp.lookup("dsWorkSittn") || mainApp.lookup("dsMain") || mainApp.lookup("dsList");
        if (!ds) {
            mainApp.getContainer().getAllRecursiveChildren().forEach(function(c) {
                if (c.type === "grid" && c.getBindDataset) ds = c.getBindDataset();
            });
        }
        if (!ds) return {error: "ds not found"};
        
        var cols = ds.getColumnNames();
        var row0 = {};
        cols.forEach(function(c) { row0[c] = ds.getValue(0, c); });
        
        // 첫 번째 행 체크 필드에 'Y' 또는 true 대입 시도
        cols.forEach(function(col) {
            if (col.indexOf("chk") >= 0 || col.indexOf("sel") >= 0 || col.indexOf("check") >= 0 || col.indexOf("mark") >= 0) {
                ds.setValue(0, col, "Y");
            }
        });
        
        var grid = mainApp.lookup("grdWorkSittn") || mainApp.lookup("grdMain") || mainApp.lookup("grdList");
        if (grid && grid.selectRows) grid.selectRows([0]);
        
        var btnRtrvl = mainApp.lookup("btnRtrvl");
        if (btnRtrvl) { btnRtrvl.click(); }
        
        return {cols: cols, row0: row0};
    })();
    """
    res = await page.evaluate(js_check_cols)
    print("\n================ [그리드 데이터셋 컬럼 및 체크필드 스캔] ================")
    print("RES:", res)
    await asyncio.sleep(2.0)
    
    # 뜬 모달 스캔 및 클릭
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
                    if (c.id === "btnOk" || c.id === "btnConfirm" || c.id === "btnYes" || val === "확인" || val === "예" || val === "OK") {
                        if (typeof c.click === 'function') c.click();
                    }
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
