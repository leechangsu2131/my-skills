#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import os
import json

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
    
    # 1) 결재선 기안 팝업(wam_woapm07_p00)에서 [결재자지정](btnSelectSancr) 클릭
    js_click_select = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var drftApp = apps.find(function(ai) { return ai && ai.app && ai.app.id.indexOf("wam_woapm07_p00") >= 0; });
        if (!drftApp) return {error: "기안 앱(wam_woapm07_p00) 미발견"};
        var btn = drftApp.lookup("btnSelectSancr");
        if (btn) { btn.click(); return {ok: true}; }
        return {error: "btnSelectSancr not found"};
    })();
    """
    res_sel = await page.evaluate(js_click_select)
    print("\n[결재자지정 버튼 클릭 결과]:", res_sel)
    await asyncio.sleep(2.5)
    
    # 2) 결재선 선택 팝업(wam_woapm07_p04)에서 교무(강동휘), 교감(김경영), 교장 순차 선택
    approvers = ["강동휘", "김경영"]
    for name in approvers:
        js_add = """
        (function() {
            var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
            var pop = apps.find(function(ai) { return ai && ai.app && ai.app.id.indexOf("wam_woapm07_p04") >= 0; });
            if (!pop) return {error: "p04 팝업 없음"};
            
            var dsMain = pop.lookup("dsMain");
            var grdUserListFrom = pop.lookup("grdUserListFrom");
            var btnAdd = pop.lookup("btn1");
            if (!dsMain || !grdUserListFrom) return {error: "ds/grid not found"};
            
            var targetRow = -1;
            for (var i = 0; i < dsMain.getRowCount(); i++) {
                if (dsMain.getValue(i, "userNm") === "TARGET_NAME") {
                    targetRow = i;
                    break;
                }
            }
            if (targetRow === -1) return {error: "TARGET_NAME 미발견"};
            
            grdUserListFrom.selectRows([targetRow]);
            if (btnAdd) btnAdd.click();
            return {ok: true, name: "TARGET_NAME", row: targetRow};
        })();
        """.replace("TARGET_NAME", name)
        res_add = await page.evaluate(js_add)
        print(f"  -> 결재자 '{name}' 추가 결과:", res_add)
        await asyncio.sleep(1.5)
        
    # 교장 추가
    js_add_principal = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var pop = apps.find(function(ai) { return ai && ai.app && ai.app.id.indexOf("wam_woapm07_p04") >= 0; });
        if (!pop) return {error: "p04 없음"};
        
        var dsMain = pop.lookup("dsMain");
        var grdUserListFrom = pop.lookup("grdUserListFrom");
        var btnAdd = pop.lookup("btn1");
        if (!dsMain) return {error: "dsMain not found"};
        
        var cols = dsMain.getColumnNames();
        var targetRow = -1;
        var principalName = "";
        
        for (var i = 0; i < dsMain.getRowCount(); i++) {
            for (var j = 0; j < cols.length; j++) {
                var val = dsMain.getValue(i, cols[j]) || "";
                if (val === "교장" || val.indexOf("교장") >= 0) {
                    targetRow = i;
                    principalName = dsMain.getValue(i, "userNm") || dsMain.getValue(i, "empNm") || "?";
                    break;
                }
            }
            if (targetRow >= 0) break;
        }
        
        if (targetRow === -1) return {error: "교장을 찾지 못함"};
        
        grdUserListFrom.selectRows([targetRow]);
        if (btnAdd) btnAdd.click();
        return {ok: true, name: principalName, row: targetRow};
    })();
    """
    res_pr = await page.evaluate(js_add_principal)
    print("  -> 교장 자동 추가 결과:", res_pr)
    await asyncio.sleep(1.5)
    
    # 3) 결재선 저장 (p04 btn4)
    js_save_line = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var pop = apps.find(function(ai) { return ai && ai.app && ai.app.id.indexOf("wam_woapm07_p04") >= 0; });
        if (!pop) return false;
        var btnSave = pop.lookup("btn4");
        if (btnSave) { btnSave.click(); return true; }
        return false;
    })();
    """
    res_line_save = await page.evaluate(js_save_line)
    print("  -> 결재선 저장 클릭 결과:", res_line_save)
    await asyncio.sleep(2.0)
    
    # 스캔: 지정 후 결재선 기안 창의 결재자 목록 스캔
    js_scan = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var drftApp = apps.find(function(ai) { return ai && ai.app && ai.app.id.indexOf("wam_woapm07_p00") >= 0; });
        if (!drftApp) return {error: "drftApp not found"};
        var texts = [];
        drftApp.getContainer().getAllRecursiveChildren().forEach(function(c) {
            var t = c.value || c.text || "";
            if (t) texts.push(t.toString().trim());
        });
        return {appId: drftApp.app.id, texts: texts};
    })();
    """
    scan_res = await page.evaluate(js_scan)
    print("\n================ [결재선 지정 스캔 및 검증 리뷰] ================")
    print("  [APP] ID:", scan_res.get("appId"))
    safe_texts = [t.encode('ascii', 'backslashreplace').decode() for t in scan_res.get("texts", [])[:20]]
    print("  [TEXTS]:", safe_texts)
    
    await pw.stop()

if __name__ == "__main__":
    asyncio.run(main())
