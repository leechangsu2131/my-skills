#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""교외체험학습보고서관리 및 결석신고서관리 메뉴 검색 오픈 및 앱 구조 진단 스크립트."""

import io, sys, time, json
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

opts = Options()
opts.add_experimental_option("debuggerAddress", "localhost:9222")
driver = webdriver.Chrome(options=opts)

for handle in driver.window_handles:
    driver.switch_to.window(handle)
    driver.switch_to.default_content()
    try:
        if driver.execute_script("return typeof cpr !== 'undefined';") and "vpn" not in driver.current_url.lower():
            break
    except: pass

print(f"[connect] {driver.title}")

def open_menu_via_search(driver, name: str) -> bool:
    print(f"  -> '{name}' 메뉴 검색 및 오픈 시도...")
    
    # 1) 검색창에 텍스트 입력 및 search 이벤트 발생
    js_search = """
    var inst = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
        return ai.app && ai.app.id === "app/com/main/Index";
    });
    if (!inst) return {error: "Index app not found"};
    
    var searchInput = inst.lookup("siFindMenu");
    var btnSearch = inst.lookup("btnSearch");
    if (!searchInput) return {error: "siFindMenu not found"};
    
    searchInput.value = "TARGET_NAME";
    if (typeof searchInput.dispatchEvent === 'function') {
        var event = new cpr.events.CUIEvent("search");
        searchInput.dispatchEvent(event);
        return {ok: true};
    }
    return {error: "dispatchEvent not supported"};
    """.replace("TARGET_NAME", name)
    
    res = driver.execute_script(js_search)
    if res.get("error"):
        print(f"    [오류] 검색 실패: {res['error']}")
        return False
        
    time.sleep(2.0)
    
    # 2) 검색 결과 리스트에서 메뉴 클릭
    js_click = """
    var all = document.querySelectorAll('*');
    for (var i = 0; i < all.length; i++) {
        var el = all[i];
        var text = (el.innerText || el.textContent || "").trim();
        if (text === "TARGET_NAME" && (el.tagName === "SPAN" || el.tagName === "DIV" || el.tagName === "A")) {
            el.click();
            return {ok: true};
        }
    }
    return {error: "menu text TARGET_NAME not found"};
    """.replace("TARGET_NAME", name)
    
    res_click = driver.execute_script(js_click)
    if res_click.get("error"):
        print(f"    [오류] 클릭 실패: {res_click['error']}")
        return False
        
    print(f"    '{name}' 메뉴 오픈 성공!")
    time.sleep(3.0) # 로딩 대기
    return True

# 두 개의 메뉴 오픈
print("=== [메뉴 오픈 시퀀스 시작] ===")
open_menu_via_search(driver, "교외체험학습보고서관리")
open_menu_via_search(driver, "결석신고서관리")

# 3) 현재 띄워진 모든 앱 구조 진단 덤프 저장
JS_DIAGNOSE_ALL = """
var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
var appList = [];
instances.forEach(function(ai, idx) {
    if (!ai || !ai.app) return;
    
    var container = ai.getContainer();
    var ctrls = [];
    container.getAllRecursiveChildren().forEach(function(ctrl) {
        var val = (ctrl.value || ctrl.text || ctrl.fieldLabel || "").toString().substring(0, 80);
        ctrls.push({id: ctrl.id || "", type: ctrl.type || "", val: val});
    });
    
    var datasets = [];
    var dc = ai.getAllDataControls ? ai.getAllDataControls() : [];
    dc.forEach(function(ds) {
        var cols = [];
        try {
            if (ds.getColumnNames) cols = ds.getColumnNames();
        } catch(e) {}
        datasets.push({id: ds.id || "", rowCount: ds.getRowCount ? ds.getRowCount() : null, cols: cols});
    });
    
    appList.push({
        idx: idx,
        appId: ai.app.id,
        title: ai.title || "",
        controls: ctrls,
        datasets: datasets
    });
});
return appList;
"""

print("\n=== [앱 인스턴스 전체 진단 실행] ===")
res_diagnose = driver.execute_script(JS_DIAGNOSE_ALL)
dump_path = "scratch/neis_reports_diagnose.json"
with open(dump_path, "w", encoding="utf-8") as f:
    json.dump(res_diagnose, f, ensure_ascii=False, indent=2)
print(f"진단 덤프 파일 저장 성공: {dump_path}")

# 핵심 덤프 요약 출력
for app in res_diagnose:
    app_id = app["appId"]
    if "Index" not in app_id and "Dashboard" not in app_id and "udc" not in app_id:
        print(f"\n[app] {app_id} | Title: '{app['title']}'")
        for ds in app["datasets"][:5]:
            print(f"  - ds: {ds['id']} (rows: {ds['rowCount']}) | cols: {ds['cols'][:8]}")
        print("  - buttons:")
        for ctrl in app["controls"]:
            if ctrl["type"] == "button":
                print(f"    * {ctrl['id']} ('{ctrl['val']}')")
