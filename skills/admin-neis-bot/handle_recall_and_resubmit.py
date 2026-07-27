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
                
    # ── 1) 메인 화면에서 1차(740) 또는 2차(741) 선택 후 회수(btnRtrvl) 실행 ──
    print("  -> [STEP 1] 메인 그리드에서 진행 중인 연수 상신건 회수(btnRtrvl) 시도...")
    js_rtrvl = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var mainApp = apps.find(function(ai) { return ai.app && ai.app.id === "edu/ga/srv/mym/mm/srv_mymmm00_m00"; });
        if (!mainApp) return {error: "mainApp not found"};
        
        var ds = mainApp.lookup("dsWorkSittn") || mainApp.lookup("dsMain") || mainApp.lookup("dsList");
        var grid = mainApp.lookup("grdWorkSittn") || mainApp.lookup("grdMain") || mainApp.lookup("grdList");
        if (!ds || !grid) return {error: "ds/grid not found"};
        
        var targetRows = [];
        for (var i = 0; i < ds.getRowCount(); i++) {
            var sclf = ds.getValue(i, "workSittnSclfCd");
            var st = ds.getValue(i, "atrzStsCd");
            if (sclf === "W0801" && (st === "1" || st === 1)) {
                targetRows.push(i);
            }
        }
        if (targetRows.length === 0) return {error: "상신 진행 중인 41조 연수가 없습니다"};
        
        grid.selectRows(targetRows);
        var btnRtrvl = mainApp.lookup("btnRtrvl");
        if (btnRtrvl) { btnRtrvl.click(); return {ok: true, rowsCount: targetRows.length, selectedRows: targetRows}; }
        return {error: "btnRtrvl not found"};
    })();
    """
    res_rtrvl = await page.evaluate(js_rtrvl)
    print("  [OK] 회수 클릭 결과:", res_rtrvl)
    await asyncio.sleep(2.0)
    
    # 뜬 알림 팝업 [확인/예] 처리
    js_confirm = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var clicked = false;
        apps.forEach(function(ai) {
            if (!ai || !ai.app) return;
            var aid = ai.app.id || "";
            if (aid.indexOf("alert") >= 0 || aid.indexOf("confirm") >= 0 || aid.indexOf("cmn") >= 0) {
                ai.getContainer().getAllRecursiveChildren().forEach(function(c) {
                    var id = c.id || "";
                    var val = (c.value || c.text || "").toString().trim();
                    if (id === "btnOk" || id === "btnConfirm" || id === "btnYes" || val === "확인" || val === "예" || val === "OK") {
                        if (typeof c.click === 'function') { c.click(); clicked = true; }
                    }
                });
            }
        });
        return clicked;
    })();
    """
    for k in range(3):
        c_res = await page.evaluate(js_confirm)
        print(f"    - 모달 닫기 {k+1}회:", c_res)
        await asyncio.sleep(1.5)
        
    await pw.stop()

if __name__ == "__main__":
    asyncio.run(main())
