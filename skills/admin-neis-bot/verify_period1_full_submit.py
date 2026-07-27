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
    
    # ── STEP 1: 메인 화면 [신청] 버튼 클릭 ──
    print("  -> [STEP 1] 메인 화면 [신청] 버튼 클릭...")
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
    
    # ── STEP 2: 복무 팝업 데이터 입력 (1차: 7.28~7.31 오후만) ──
    print("  -> [STEP 2] 복무 신청 팝업 데이터 입력 (1차: 7.28~7.31 오후)...")
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
        
        setValAndDispatch("ipbDestiNm", "경주 화천");
        setValAndDispatch("ipbWorkSittnRsnCn", "교육연극을 활용한 국어수업 연구");
        setValAndDispatch("txaWorkSittnRsnCn", "교육연극을 활용한 국어수업 연구");
        
        var btnAprv = popApp.lookup("btnAprvDmnd");
        if (btnAprv) { btnAprv.click(); return {ok: true}; }
        return {error: "btnAprvDmnd not found"};
    })();
    """
    res_fill = await page.evaluate(js_fill)
    print("  [OK] 폼 입력 및 [승인요청] 클릭:", res_fill)
    await asyncio.sleep(4.0)
    
    # ── STEP 3: 결재선 지정 (강동휘, 김경영, 박순현 교장) ──
    print("  -> [STEP 3] 결재선 지정 팝업 연결...")
    js_click_select = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var drftApp = apps.find(function(ai) { return ai && ai.app && ai.app.id.indexOf("wam_woapm07_p00") >= 0; });
        if (!drftApp) return {error: "wam_woapm07_p00 not found"};
        var btn = drftApp.lookup("btnSelectSancr");
        if (!btn) return {error: "btnSelectSancr not found"};
        if (btn.enabled === false) return {error: "btnSelectSancr disabled"};
        btn.click();
        return {ok: true};
    })();
    """
    for i in range(15):
        res_sel = await page.evaluate(js_click_select)
        if res_sel and res_sel.get("ok"):
            print(f"    [OK] 결재자지정 버튼 클릭 성공 ({i+1}초 감지)")
            break
        await asyncio.sleep(1.0)
        
    print("    -> 결재선 선택 팝업(wam_woapm07_p04) 오픈 대기 (10초 폴링)...")
    js_check_p04 = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var pop = apps.find(function(ai) { return ai && ai.app && ai.app.id.indexOf("wam_woapm07_p04") >= 0; });
        return pop ? true : false;
    })();
    """
    for _ in range(10):
        if await page.evaluate(js_check_p04):
            break
        await asyncio.sleep(1.0)
    await asyncio.sleep(1.5)
    
    # 결재자 추가
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
                if (dsMain.getValue(i, "userNm") === "TARGET_NAME") { targetRow = i; break; }
            }
            if (targetRow === -1) return {error: "TARGET_NAME 미발견"};
            grdUserListFrom.selectRows([targetRow]);
            if (btnAdd) btnAdd.click();
            return {ok: true, name: "TARGET_NAME", row: targetRow};
        })();
        """.replace("TARGET_NAME", name)
        r_a = await page.evaluate(js_add)
        print(f"    - 결재자 {name} 추가:", r_a)
        await asyncio.sleep(1.5)
        
    # 교장 자동 추가
    js_add_pr = """
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
        if (targetRow === -1) return {error: "교장 미발견"};
        grdUserListFrom.selectRows([targetRow]);
        if (btnAdd) btnAdd.click();
        return {ok: true, name: principalName, row: targetRow};
    })();
    """
    r_pr = await page.evaluate(js_add_pr)
    print("    - 교장 자동 추가:", r_pr)
    await asyncio.sleep(1.5)
    
    # 결재선 저장 (p04 btn4)
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
    await page.evaluate(js_save_line)
    await asyncio.sleep(2.5)
    
    # ── STEP 4: 기안 팝업에서 최종 [상신] 클릭 및 컨펌 [확인/예] 다이얼로그 누르기 ──
    print("  -> [STEP 4] 최종 [상신] (btnDrft/btnDrftBottom) 클릭...")
    js_click_drft = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var drftApp = apps.find(function(ai) { return ai && ai.app && ai.app.id.indexOf("wam_woapm07_p00") >= 0; });
        if (!drftApp) return {error: "drftApp not found"};
        var btn = drftApp.lookup("btnDrft") || drftApp.lookup("btnDrftBottom");
        if (btn) { btn.click(); return {ok: true, btnId: btn.id}; }
        return {error: "btnDrft not found"};
    })();
    """
    res_drft = await page.evaluate(js_click_drft)
    print("  [OK] [상신] 버튼 클릭 결과:", res_drft)
    await asyncio.sleep(2.5)
    
    # 상신 컨펌 다이얼로그 [확인/예] 클릭 4회 연속
    js_confirm_modal = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var clicked = false;
        var logs = [];
        apps.forEach(function(ai) {
            if (!ai || !ai.app) return;
            var aid = ai.app.id || "";
            if (aid.indexOf("confirm") >= 0 || aid.indexOf("alert") >= 0 || aid.indexOf("cmn") >= 0) {
                logs.push(aid);
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
        return {clicked: clicked, logs: logs};
    })();
    """
    for i in range(5):
        c_res = await page.evaluate(js_confirm_modal)
        print(f"    - 상신 컨펌 클릭 {i+1}회:", c_res)
        await asyncio.sleep(2.0)
        
    # ── STEP 5: 최종 메인 결재상태 스캔 ──
    print("\n================ [1차 연수 상신 후 최종 메인 결재상태 스캔] ================")
    js_scan_grid = """
    (function() {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var mainApp = apps.find(function(ai) { return ai.app && ai.app.id === "edu/ga/srv/mym/mm/srv_mymmm00_m00"; });
        if (!mainApp) return {error: "mainApp not found"};
        
        var grid = mainApp.lookup("grdWorkSittn") || mainApp.lookup("grdMain") || mainApp.lookup("grdList");
        if (!grid) return {error: "grid not found"};
        var ds = grid.getDataSet ? grid.getDataSet() : null;
        var rows = [];
        if (ds && ds.getRowCount) {
            var cols = ds.getColumnNames();
            for (var i = 0; i < ds.getRowCount(); i++) {
                var rowObj = {};
                cols.forEach(function(col) {
                    rowObj[col] = ds.getValue(i, col);
                });
                rows.push(rowObj);
            }
        }
        return {rowCount: rows.length, rows: rows.slice(0, 5)};
    })();
    """
    grid_res = await page.evaluate(js_scan_grid)
    print("GRID ROWS:", grid_res)
    
    await pw.stop()

if __name__ == "__main__":
    asyncio.run(main())
