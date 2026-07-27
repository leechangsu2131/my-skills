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
                
    # 7월~8월 전체 조회조건 설정 후 조회 클릭
    js_set_range_and_search = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var mainApp = apps.find(function(ai) { return ai.app && ai.app.id === "edu/ga/srv/mym/mm/srv_mymmm00_m00"; });
        if (!mainApp) return {error: "mainApp not found"};
        
        var dmSearch = mainApp.lookup("dmSearch");
        if (dmSearch) {
            try { dmSearch.setValue("bgngYmd", "20260701"); } catch(e) {}
            try { dmSearch.setValue("endYmd", "20260831"); } catch(e) {}
        }
        
        var ipbB = mainApp.lookup("ipbBgngYmd");
        var ipbE = mainApp.lookup("ipbEndYmd");
        if (ipbB) ipbB.value = "20260701";
        if (ipbE) ipbE.value = "20260831";
        
        var btnSearch = mainApp.lookup("btnSearch");
        if (btnSearch) { btnSearch.click(); return {ok: true}; }
        return {error: "btnSearch not found"};
    })();
    """
    res = await page.evaluate(js_set_range_and_search)
    print("  [OK] 조회범위 20260701~20260831 설정 및 클릭:", res)
    await asyncio.sleep(2.0)
    
    js_scan_status = """
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
        var rows = [];
        if (ds && ds.getRowCount) {
            var cols = ds.getColumnNames();
            for (var i = 0; i < ds.getRowCount(); i++) {
                var item = {};
                cols.forEach(function(col) {
                    var v = ds.getValue(i, col);
                    if (v !== null && v !== undefined) item[col] = v;
                });
                rows.push(item);
            }
        }
        return {rowCount: rows.length, rows: rows};
    })();
    """
    res_scan = await page.evaluate(js_scan_status)
    print("\n================ [7월~8월 전체 기간 스캔 결과] ================")
    print(f"총 신청 건수: {res_scan.get('rowCount')}건")
    for idx, r in enumerate(res_scan.get("rows", [])):
        print(f"\n[ROW {idx+1}] DATA:")
        for k, v in r.items():
            if "ymd" in k.lower() or "sittn" in k.lower() or "rsn" in k.lower() or "desti" in k.lower() or "st" in k.lower() or "stat" in k.lower() or "aprv" in k.lower() or "sanc" in k.lower():
                safe_v = str(v).encode('ascii', 'backslashreplace').decode()
                print(f"    - {k:25} = {safe_v}")
                
    await pw.stop()

if __name__ == "__main__":
    asyncio.run(main())
