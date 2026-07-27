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
    
    # 1) 메인 화면에서 [신청] 버튼 클릭
    js_click_apply = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var mainApp = apps.find(function(ai) { return ai.app && ai.app.id === "edu/ga/srv/mym/mm/srv_mymmm00_m00"; });
        if (!mainApp) return {error: "mainApp not found"};
        var btn = mainApp.lookup("btnAply");
        if (btn) { btn.click(); return {ok: true}; }
        return {error: "btnAply not found"};
    })();
    """
    await page.evaluate(js_click_apply)
    await asyncio.sleep(2.5)
    
    # 2) 복무 팝업에 W08(연수), W0801(41조 연수), 1차 날짜(7.28~7.31 오후), 목적지, 사유 대입
    js_fill = """
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
        
        setValAndDispatch("cmbWorkSittnLclfCd", "W08");
        setValAndDispatch("cmbWorkSittnSclfCd", "W0801");
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
    res_fill = await page.evaluate(js_fill)
    print("\n[STEP 1 - 1차 41조(W08/W0801) 입력 및 승인요청 클릭 결과]:", res_fill)
    await asyncio.sleep(2.5)
    
    # 3) 결과 스캔 (생성된 앱과 텍스트 추출)
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
    print("\n================ [1차 연수 1건 단일 스캔 및 상태 리뷰] ================")
    for item in scan_res:
        if "cmn" in item["appId"] or "alert" in item["appId"] or "confirm" in item["appId"] or "wam" in item["appId"]:
            print(f"  [APP] ID: {item['appId']}")
            safe_texts = [t.encode('ascii', 'backslashreplace').decode() for t in item['texts'][:10]]
            print(f"        TEXTS: {safe_texts}")
            
    await pw.stop()

if __name__ == "__main__":
    asyncio.run(main())
