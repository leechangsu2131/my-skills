#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""탭 폴더에서 교외체험학습신청서관리 탭 자동 활성화 테스트."""

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

JS_ACTIVATE_TAB = r"""
return (function() {
    // 1) eXBuilder 탭폴더 아이템들 중 "교외체험학습신청서관리" 검색
    var tabs = document.querySelectorAll('.cl-tabfolder-item, [role="tab"], .cl-tab, a, span');
    var targetTab = null;
    for (var i = 0; i < tabs.length; i++) {
        var text = (tabs[i].innerText || tabs[i].textContent || "").trim();
        if (text === "교외체험학습신청서관리") {
            targetTab = tabs[i];
            break;
        }
    }
    
    if (targetTab) {
        targetTab.click();
        return {ok: true, message: "Tab found and clicked!", tagName: targetTab.tagName};
    }
    
    // 2) 만약 탭이 없다면 전체 메뉴 트리에서 찾기 시도
    // 트리 노드 중 "교외체험학습신청서관리" 검색
    var treeItems = document.querySelectorAll('.cl-tree-item, .cl-tree, span, a');
    var targetTreeItem = null;
    for (var i = 0; i < treeItems.length; i++) {
        var text = (treeItems[i].innerText || treeItems[i].textContent || "").trim();
        if (text === "교외체험학습신청서관리") {
            targetTreeItem = treeItems[i];
            break;
        }
    }
    
    if (targetTreeItem) {
        targetTreeItem.click();
        return {ok: true, message: "Tree item found and clicked!", tagName: targetTreeItem.tagName};
    }

    return {error: "Tab or Tree item not found"};
})();
"""

res = driver.execute_script(JS_ACTIVATE_TAB)
print(res)
