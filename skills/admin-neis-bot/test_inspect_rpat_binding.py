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
                
    # 메인 [신청] 클릭
    await page.evaluate("""
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var mainApp = apps.find(function(ai) { return ai.app && ai.app.id === "edu/ga/srv/mym/mm/srv_mymmm00_m00"; });
        if (mainApp) mainApp.lookup("btnAply").click();
    })();
    """)
    await asyncio.sleep(2.0)
    
    # cbxDdRpatYn 바인딩 데이터맵/데이터셋 필드 인스펙트
    js_inspect_rpat_dm = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var popApp = apps.find(function(ai) {
            return ai.app && (ai.app.id.indexOf("srv_mymmm00_p00") >= 0 || ai.app.id.indexOf("srv_mymmm00_p") >= 0) && ai.app.id !== "edu/ga/srv/mym/mm/srv_mymmm00_m00";
        });
        if (!popApp) return {error: "popApp not found"};
        
        var cbxDd = popApp.lookup("cbxDdRpatYn");
        var bindInfo = cbxDd ? (cbxDd.getBindInfo ? cbxDd.getBindInfo("value") : null) : null;
        
        // DataMap / DataSet 전수 스캔
        var dmObj = {};
        popApp.getAllDataControls().forEach(function(dc) {
            if (dc.getValue) {
                try {
                    dc.getColumnNames().forEach(function(col) {
                        if (col.indexOf("Rpat") >= 0 || col.indexOf("rpat") >= 0 || col.indexOf("dd") >= 0) {
                            dmObj[dc.id + "." + col] = dc.getValue(col);
                        }
                    });
                } catch(e) {}
            }
        });
        
        return {
            cbxVal: cbxDd ? cbxDd.value : null,
            bindInfo: bindInfo,
            dmObj: dmObj
        };
    })();
    """
    res1 = await page.evaluate(js_inspect_rpat_dm)
    print("\n================ [체크 전 ddRpatYn 바인딩 인스펙트] ================")
    print("RES 1:", res1)
    
    # cbxDdRpatYn 의 value 를 Y 로 설정하고 데이터맵 값 변화 확인
    js_set_and_check = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var popApp = apps.find(function(ai) {
            return ai.app && (ai.app.id.indexOf("srv_mymmm00_p00") >= 0 || ai.app.id.indexOf("srv_mymmm00_p") >= 0) && ai.app.id !== "edu/ga/srv/mym/mm/srv_mymmm00_m00";
        });
        if (!popApp) return {error: "popApp not found"};
        
        var cbxDd = popApp.lookup("cbxDdRpatYn");
        if (cbxDd) {
            cbxDd.value = "Y";
            try { cbxDd.redraw(); } catch(e) {}
            try { cbxDd.dispatchEvent(new cpr.events.CValueChangeEvent("value-change", {oldValue: "N", newValue: "Y"})); } catch(e) {}
        }
        
        // DataMap 변경사항 확인 및 강제 Y 대입
        popApp.getAllDataControls().forEach(function(dc) {
            if (dc.setValue) {
                try {
                    dc.getColumnNames().forEach(function(col) {
                        if (col.indexOf("Rpat") >= 0 || col.indexOf("rpat") >= 0 || col === "ddRpatYn") {
                            dc.setValue(col, "Y");
                        }
                    });
                } catch(e) {}
            }
        });
        
        var dmObj = {};
        popApp.getAllDataControls().forEach(function(dc) {
            if (dc.getValue) {
                try {
                    dc.getColumnNames().forEach(function(col) {
                        if (col.indexOf("Rpat") >= 0 || col.indexOf("rpat") >= 0 || col.indexOf("dd") >= 0) {
                            dmObj[dc.id + "." + col] = dc.getValue(col);
                        }
                    });
                } catch(e) {}
            }
        });
        return {cbxVal: cbxDd ? cbxDd.value : null, dmObj: dmObj};
    })();
    """
    res2 = await page.evaluate(js_set_and_check)
    print("\n================ [Y 설정 및 DataMap 강제 대입 후 인스펙트] ================")
    print("RES 2:", res2)
    
    # 팝업 닫기
    await page.evaluate("""
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var popApp = apps.find(function(ai) {
            return ai.app && (ai.app.id.indexOf("srv_mymmm00_p00") >= 0 || ai.app.id.indexOf("srv_mymmm00_p") >= 0) && ai.app.id !== "edu/ga/srv/mym/mm/srv_mymmm00_m00";
        });
        if (popApp && popApp.lookup("btnClose")) popApp.lookup("btnClose").click();
    })();
    """)
    
    await pw.stop()

if __name__ == "__main__":
    asyncio.run(main())
