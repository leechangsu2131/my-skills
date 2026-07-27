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
                
    js_scan_clean = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var mainApp = apps.find(function(ai) { return ai.app && ai.app.id === "edu/ga/srv/mym/mm/srv_mymmm00_m00"; });
        if (!mainApp) return {error: "mainApp not found"};
        
        var ds = mainApp.lookup("dsWorkSittn") || mainApp.lookup("dsMain") || mainApp.lookup("dsList");
        var rows = [];
        if (ds && ds.getRowCount) {
            for (var i = 0; i < ds.getRowCount(); i++) {
                rows.push({
                    sn: ds.getValue(i, "workSittnSn"),
                    sclfNm: ds.getValue(i, "workSittnSclfNm"),
                    prd: ds.getValue(i, "workSittnPrd"),
                    ttl: ds.getValue(i, "workSittnTtl"),
                    tel: ds.getValue(i, "emgCnctTelno"),
                    desti: ds.getValue(i, "destiNm"),
                    sts: ds.getValue(i, "prgStsNm"),
                    stsCd: ds.getValue(i, "atrzStsCd")
                });
            }
        }
        return {rowCount: rows.length, rows: rows};
    })();
    """
    res = await page.evaluate(js_scan_clean)
    print("\n================ [메인 근무상황 한눈에 정밀 요약 스캔] ================")
    print(f"총 건수: {res.get('rowCount')}건")
    for idx, r in enumerate(res.get("rows", [])):
        safe_sclf = str(r['sclfNm']).encode('ascii', 'backslashreplace').decode()
        safe_prd = str(r['prd']).encode('ascii', 'backslashreplace').decode()
        safe_ttl = str(r['ttl']).encode('ascii', 'backslashreplace').decode()
        safe_tel = str(r['tel']).encode('ascii', 'backslashreplace').decode()
        safe_dest = str(r['desti']).encode('ascii', 'backslashreplace').decode()
        safe_sts = str(r['sts']).encode('ascii', 'backslashreplace').decode()
        print(f"[{idx+1:2}] Sn={r['sn']:5} | 구분={safe_sclf:12} | 기간={safe_prd:36} | 총시간={safe_ttl:15} | 연락처={safe_tel:13} | 목적지={safe_dest:10} | 상태={safe_sts} ({r['stsCd']})")
        
    await pw.stop()

if __name__ == "__main__":
    asyncio.run(main())
