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
    
    # [단일 건 1단계] 1차 기간(7.28~7.31 오후) 신청 폼 채우기 및 승인요청 시도
    js_test_step1 = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var mainApp = apps.find(function(ai) { return ai.app && ai.app.id === "edu/ga/srv/mym/mm/srv_mymmm00_m00"; });
        if (!mainApp) return {error: "mainApp not found"};
        
        var btnAply = mainApp.lookup("btnAply");
        if (btnAply) btnAply.click();
        return {ok: true};
    })();
    """
    await page.evaluate(js_test_step1)
    await asyncio.sleep(2.5)
    
    js_fill_first = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var popApp = apps.find(function(ai) {
            return ai.app && (ai.app.id.indexOf("srv_mymmm00_p00") >= 0 || ai.app.id.indexOf("srv_mymmm00_p") >= 0) && ai.app.id !== "edu/ga/srv/mym/mm/srv_mymmm00_m00";
        });
        if (!popApp) return {error: "popApp (srv_mymmm00_p00) not found"};
        
        function setValAndDispatch(id, val) {
            var c = popApp.lookup(id);
            if (!c) return false;
            var old = c.value;
            c.value = val;
            try { c.redraw(); } catch(e) {}
            try {
                var evt = new cpr.events.CValueChangeEvent("value-change", {oldValue: old, newValue: val});
                c.dispatchEvent(evt);
            } catch(e) {}
            try {
                var el = c.getHtmlElement ? c.getHtmlElement() : null;
                if (el) {
                    var inp = (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') ? el : el.querySelector('input, textarea');
                    if (inp) {
                        inp.value = val;
                        inp.dispatchEvent(new Event('input', { bubbles: true }));
                        inp.dispatchEvent(new Event('change', { bubbles: true }));
                        inp.dispatchEvent(new Event('blur', { bubbles: true }));
                    }
                }
            } catch(e) {}
            return true;
        }
        
        setValAndDispatch("cmbWorkSittnSclfCd", "W0105");
        setValAndDispatch("cmbAvRsnCd", "09");
        setValAndDispatch("dtiWorkYmdFrom", "20260728");
        setValAndDispatch("dtiWorkYmdTo", "20260731");
        setValAndDispatch("cmbBgngH", "12");
        setValAndDispatch("cmbBgngM", "10");
        setValAndDispatch("cmbEndH", "16");
        setValAndDispatch("cmbEndM", "40");
        
        var cbxDd = popApp.lookup("cbxDdRpatYn");
        if (cbxDd) {
            try {
                var dom = cbxDd.getHtmlElement ? cbxDd.getHtmlElement() : null;
                if (dom) dom.click();
            } catch(e) {}
        }
        
        setValAndDispatch("ipbDestiNm", "화천 자택");
        setValAndDispatch("ipbWorkSittnRsnCn", "교육연극을 활용한 국어수업 연구");
        setValAndDispatch("txaWorkSittnRsnCn", "교육연극을 활용한 국어수업 연구");
        
        var btnAprv = popApp.lookup("btnAprvDmnd");
        if (btnAprv) { btnAprv.click(); return {ok: true}; }
        return {error: "btnAprvDmnd not found"};
    })();
    """
    res_fill = await page.evaluate(js_fill_first)
    print("\n[STEP 1 - 1차 기간(7.28~7.31) 입력 결과]:", res_fill)
    await asyncio.sleep(2.0)
    
    # 스캔: 클릭 후 떠 있는 alert/confirm 및 화면 앱 스캔
    js_scan = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var scanned = [];
        apps.forEach(function(ai) {
            if (!ai || !ai.app) return;
            var aid = ai.app.id || "";
            var texts = [];
            try {
                ai.getContainer().getAllRecursiveChildren().forEach(function(c) {
                    var t = c.value || c.text || "";
                    if (t) texts.push(t.toString().trim());
                });
            } catch(e) {}
            scanned.push({appId: aid, texts: texts});
        });
        return scanned;
    })();
    """
    scan_res = await page.evaluate(js_scan)
    print("\n================ [화면 스캔 및 모달 상태 리뷰] ================")
    for item in scan_res:
        if "cmn" in item["appId"] or "alert" in item["appId"] or "confirm" in item["appId"] or "wam" in item["appId"]:
            print(f"  [APP] ID: {item['appId']}")
            safe_texts = [t.encode('ascii', 'backslashreplace').decode() for t in item['texts'][:10]]
            print(f"        TEXTS: {safe_texts}")
            
    await pw.stop()

if __name__ == "__main__":
    asyncio.run(main())
