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
                
    # dmSearch 의 모든 컬럼명 스캔 및 20260701~20260831 설정
    js_inspect_dm_search = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var mainApp = apps.find(function(ai) { return ai.app && ai.app.id === "edu/ga/srv/mym/mm/srv_mymmm00_m00"; });
        if (!mainApp) return {error: "mainApp not found"};
        
        var dmSearch = mainApp.lookup("dmSearch");
        var dmInfo = {};
        if (dmSearch) {
            dmSearch.getColumnNames().forEach(function(c) {
                dmInfo[c] = dmSearch.getValue(c);
                if (c.indexOf("Ymd") >= 0 || c.indexOf("ymd") >= 0 || c.indexOf("bgng") >= 0 || c.indexOf("end") >= 0 || c.indexOf("Date") >= 0) {
                    if (c.indexOf("bgng") >= 0 || c.indexOf("Bgng") >= 0) dmSearch.setValue(c, "20260701");
                    if (c.indexOf("end") >= 0 || c.indexOf("End") >= 0) dmSearch.setValue(c, "20260831");
                }
            });
        }
        
        var btnSearch = mainApp.lookup("btnSearch");
        if (btnSearch) btnSearch.click();
        
        return {dmInfo: dmInfo};
    })();
    """
    res = await page.evaluate(js_inspect_dm_search)
    print("\n================ [dmSearch 데이터맵 컬럼 및 세팅 스캔] ================")
    print("RES:", res)
    await asyncio.sleep(2.0)
    
    # 스캔
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
    print(f"\n총 신청 건수: {res_scan.get('rowCount')}건")
    for idx, r in enumerate(res_scan.get("rows", [])):
        print(f"\n[ROW {idx+1}] DATA:")
        for k, v in r.items():
            if "ymd" in k.lower() or "sittn" in k.lower() or "rsn" in k.lower() or "desti" in k.lower() or "st" in k.lower() or "stat" in k.lower() or "aprv" in k.lower() or "sanc" in k.lower():
                safe_v = str(v).encode('ascii', 'backslashreplace').decode()
                print(f"    - {k:25} = {safe_v}")
                
    await pw.stop()

if __name__ == "__main__":
    asyncio.run(main())
