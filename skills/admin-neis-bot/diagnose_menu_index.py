#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""메인 셸에서 교외체험학습신청서관리 메뉴 ID 및 이동 메서드 진단."""

import io, sys, json
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

JS_DIAGNOSE_MENU = r"""
return (function() {
    var inst = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
        return ai.app && ai.app.id === "app/com/main/Index";
    });
    if (!inst) return {error: "Index app not found"};
    
    var ds = inst.lookup("dsAllMenu");
    if (!ds) return {error: "dsAllMenu not found"};
    
    // "교외체험학습신청서관리" 메뉴 찾기
    var targetRow = -1;
    var menuInfo = null;
    for (var i = 0; i < ds.getRowCount(); i++) {
        var nm = ds.getValue(i, "MENU_NM");
        if (nm === "교외체험학습신청서관리") {
            targetRow = i;
            menuInfo = {
                row: i,
                MENU_ID: ds.getValue(i, "MENU_ID"),
                MENU_NM: ds.getValue(i, "MENU_NM"),
                UP_MENU_ID: ds.getValue(i, "UP_MENU_ID"),
                CALL_PAGE: ds.getValue(i, "CALL_PAGE"),
                PGM_ID: ds.getValue(i, "PGM_ID")
            };
            break;
        }
    }
    
    // Index 앱의 메서드 리스트 덤프 (메뉴 이동용)
    var methods = [];
    try {
        var proto = Object.getPrototypeOf(inst);
        Object.getOwnPropertyNames(proto).forEach(function(m) {
            if (m.indexOf("menu") >= 0 || m.indexOf("Menu") >= 0 || 
                m.indexOf("open") >= 0 || m.indexOf("select") >= 0 ||
                m.indexOf("click") >= 0 || m.indexOf("tab") >= 0) {
                methods.push(m);
            }
        });
    } catch(e) { methods.push("protoERR:" + e.message); }
    
    // 컨트롤 중 메뉴나 탭 관련 ID 확인
    var menuCtrls = [];
    inst.getContainer().getAllRecursiveChildren().forEach(function(c) {
        var id = c.id || "";
        var type = c.type || "";
        if (id.indexOf("menu") >= 0 || id.indexOf("Menu") >= 0 || 
            id.indexOf("tab") >= 0 || id.indexOf("Tab") >= 0 ||
            id.indexOf("tre") >= 0 || id.indexOf("Mdi") >= 0) {
            menuCtrls.push({id: id, type: type});
        }
    });

    return {
        menuInfo: menuInfo,
        methods: methods,
        menuCtrls: menuCtrls
    };
})();
"""

res = driver.execute_script(JS_DIAGNOSE_MENU)
print(json.dumps(res, ensure_ascii=False, indent=2))
