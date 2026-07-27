#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import os
import sys

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
                
    print(f"PAGE: {await page.title()}")
    
    # ── STEP 1: 회수(btnRtrvl) 실행 ──
    print("\n================ [STEP 1] 상신 진행 중인 41조 연수건 회수(btnRtrvl) ================")
    js_recall = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var mainApp = apps.find(function(ai) { return ai.app && ai.app.id === "edu/ga/srv/mym/mm/srv_mymmm00_m00"; });
        if (!mainApp) return {error: "mainApp not found"};
        
        var ds = mainApp.lookup("dsWorkSittn") || mainApp.lookup("dsMain") || mainApp.lookup("dsList");
        var grid = mainApp.lookup("grdWorkSittn") || mainApp.lookup("grdMain") || mainApp.lookup("grdList");
        if (!ds || !grid) return {error: "ds/grid not found"};
        
        var targetIdxs = [];
        for (var i = 0; i < ds.getRowCount(); i++) {
            var sclf = ds.getValue(i, "workSittnSclfCd");
            var st = ds.getValue(i, "atrzStsCd");
            if (sclf === "W0801" && (st === "1" || st === 1)) {
                targetIdxs.push(i);
            }
        }
        if (targetIdxs.length === 0) return {ok: true, recalledCount: 0, msg: "회수할 상신건이 없습니다"};
        
        if (grid.clearAllCheck) grid.clearAllCheck();
        targetIdxs.forEach(function(idx) {
            grid.setCheckRowIndex(idx, true);
        });
        
        var btnRtrvl = mainApp.lookup("btnRtrvl");
        if (btnRtrvl) {
            btnRtrvl.click();
            return {ok: true, recalledCount: targetIdxs.length, targetIdxs: targetIdxs};
        }
        return {error: "btnRtrvl not found"};
    })();
    """
    res_recall = await page.evaluate(js_recall)
    print("  [OK] 회수 실행 결과:", res_recall)
    await asyncio.sleep(2.0)
    
    # 회수 확인 다이얼로그 [확인/예] 닫기 (4회)
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
                        var id = c.id || "";
                        var val = (c.value || c.text || "").toString().trim();
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
    for k in range(4):
        c_res = await page.evaluate(js_dismiss)
        print(f"    - 회수 다이얼로그 닫기 {k+1}회:", c_res)
        await asyncio.sleep(1.5)
        
    await asyncio.sleep(2.0)
    
    # ── STEP 2: 회수된 건 삭제(btnDelete) ──
    print("\n================ [STEP 2] 회수된 건 삭제(btnDelete) 시도 ================")
    js_delete = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var mainApp = apps.find(function(ai) { return ai.app && ai.app.id === "edu/ga/srv/mym/mm/srv_mymmm00_m00"; });
        if (!mainApp) return {error: "mainApp not found"};
        
        var ds = mainApp.lookup("dsWorkSittn") || mainApp.lookup("dsMain") || mainApp.lookup("dsList");
        var grid = mainApp.lookup("grdWorkSittn") || mainApp.lookup("grdMain") || mainApp.lookup("grdList");
        if (!ds || !grid) return {error: "ds/grid not found"};
        
        var targetIdxs = [];
        for (var i = 0; i < ds.getRowCount(); i++) {
            var sclf = ds.getValue(i, "workSittnSclfCd");
            var st = ds.getValue(i, "atrzStsCd");
            if (sclf === "W0801" && (st === "9" || st === 9 || st === "8" || st === 8)) {
                targetIdxs.push(i);
            }
        }
        if (targetIdxs.length === 0) return {ok: true, deletedCount: 0, msg: "삭제할 회수건이 없습니다"};
        
        if (grid.clearAllCheck) grid.clearAllCheck();
        targetIdxs.forEach(function(idx) {
            grid.setCheckRowIndex(idx, true);
        });
        
        var btnDelete = mainApp.lookup("btnDelete");
        if (btnDelete) {
            btnDelete.click();
            return {ok: true, deletedCount: targetIdxs.length, targetIdxs: targetIdxs};
        }
        return {error: "btnDelete not found"};
    })();
    """
    res_del = await page.evaluate(js_delete)
    print("  [OK] 삭제 실행 결과:", res_del)
    await asyncio.sleep(2.0)
    
    for k in range(4):
        c_res = await page.evaluate(js_dismiss)
        print(f"    - 삭제 다이얼로그 닫기 {k+1}회:", c_res)
        await asyncio.sleep(1.5)
        
    await pw.stop()

if __name__ == "__main__":
    asyncio.run(main())
