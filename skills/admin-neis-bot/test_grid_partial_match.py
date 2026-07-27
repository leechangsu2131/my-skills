#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""그리드 DOM 요소를 부분 매치 쿼리로 탐색하는 테스트."""

import io, sys, time
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

JS_FIND_DOM_GRID = r"""
return (function() {
    var inst = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
        return ai.app && ai.app.id === "edu/sa/eds/eaa/ae/eds_eaaae01_m01";
    });
    if (!inst) return {error: "app not found"};
    
    var grid = inst.lookup("grdMain");
    if (!grid) return {error: "grdMain not found"};
    
    var uuid = grid.uuid; // "1fu"
    var id = grid.id;     // "grdMain"
    
    var res = {};
    
    // 부분 매칭 검색
    var byUuidId = document.querySelector('[id*="' + uuid + '"]');
    res.byUuidId = byUuidId ? {tag: byUuidId.tagName, id: byUuidId.id, class: byUuidId.className} : "not found";
    
    var byGridId = document.querySelector('[id*="' + id + '"]');
    res.byGridId = byGridId ? {tag: byGridId.tagName, id: byGridId.id, class: byGridId.className} : "not found";
    
    var byDataUuid = document.querySelector('[data-uuid*="' + uuid + '"]');
    res.byDataUuid = byDataUuid ? {tag: byDataUuid.tagName, id: byDataUuid.id, class: byDataUuid.className} : "not found";
    
    // 전체 body 하위에서 클래스명에 cl-grid가 들어가고 uuid가 연관된 엘리먼트 검색
    var allGrids = document.querySelectorAll('.cl-grid');
    res.allGridsCount = allGrids.length;
    var grids = [];
    allGrids.forEach(function(g) {
        grids.push({tag: g.tagName, id: g.id, class: g.className});
    });
    res.grids = grids;
    
    return res;
})();
"""

res = driver.execute_script(JS_FIND_DOM_GRID)
import json
print(json.dumps(res, ensure_ascii=False, indent=2))
