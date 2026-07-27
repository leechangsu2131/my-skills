#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""그리드 객체의 속성 및 DOM 매핑 관계 진단 스크립트."""

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

JS_DIAGNOSE_GRID_DOM = r"""
return (function() {
    var inst = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
        return ai.app && ai.app.id === "edu/sa/eds/eaa/ae/eds_eaaae01_m01";
    });
    if (!inst) return {error: "app not found"};
    
    var grid = inst.lookup("grdMain");
    if (!grid) return {error: "grdMain not found"};
    
    // grid 객체의 모든 프로퍼티 덤프
    var props = [];
    for (var k in grid) {
        props.push(k);
    }
    
    var result = {
        uuid: grid.uuid || "none",
        id: grid.id || "none",
        type: grid.type || "none",
        props: props.slice(0, 100)
    };
    
    // cpr 컴포넌트의 DOM 요소를 찾는 표준 방식
    // eXBuilder6에서는 cpr.core.Platform.INSTANCE.getDOM(grid) 또는 비슷한 전역 API가 존재합니다.
    try {
        var el = document.getElementById(grid.uuid);
        result.domByIdUuid = el ? el.tagName : "not found";
    } catch(e) { result.domByIdUuid_err = e.message; }
    
    try {
        var el2 = document.getElementById(grid.id);
        result.domByIdId = el2 ? el2.tagName : "not found";
    } catch(e) { result.domByIdId_err = e.message; }
    
    // 앱 컨테이너 DOM 내부에서 class명에 grid가 포함된 모든 요소 검색
    var containerEl = inst.getContainer().getElement ? inst.getContainer().getElement() : null;
    if (containerEl) {
        result.containerTag = containerEl.tagName;
        var subGrids = containerEl.querySelectorAll('.cl-grid, [data-uuid]');
        result.subGridsCount = subGrids.length;
        var gridList = [];
        subGrids.forEach(function(sg) {
            gridList.push({tagName: sg.tagName, className: sg.className, id: sg.id, uuid: sg.getAttribute("data-uuid")});
        });
        result.gridList = gridList;
    } else {
        result.containerTag = "no getElement method on container";
    }

    return result;
})();
"""

res = driver.execute_script(JS_DIAGNOSE_GRID_DOM)
print(json.dumps(res, ensure_ascii=False, indent=2))
