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
                
    # 메인 조회 버튼 (btnSearch) 클릭
    await page.evaluate("""
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var mainApp = apps.find(function(ai) { return ai.app && ai.app.id === "edu/ga/srv/mym/mm/srv_mymmm00_m00"; });
        if (mainApp && mainApp.lookup("btnSearch")) mainApp.lookup("btnSearch").click();
    })();
    """)
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
    res = await page.evaluate(js_scan_status)
    print("\n================ [조회 후 메인 근무상황 결재상태 스캔] ================")
    print(f"총 신청 건수: {res.get('rowCount')}건")
    for idx, r in enumerate(res.get("rows", [])):
        print(f"\n[ROW {idx+1}] DATA:")
        for k, v in r.items():
            if "ymd" in k.lower() or "sittn" in k.lower() or "rsn" in k.lower() or "desti" in k.lower() or "st" in k.lower() or "stat" in k.lower() or "aprv" in k.lower() or "sanc" in k.lower():
                safe_v = str(v).encode('ascii', 'backslashreplace').decode()
                print(f"    - {k:25} = {safe_v}")
                
    await pw.stop()

if __name__ == "__main__":
    asyncio.run(main())
