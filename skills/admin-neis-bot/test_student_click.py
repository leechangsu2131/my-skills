#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""그리드 내 학생명 텍스트 기반 클릭 테스트 스크립트."""

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

# 학생명 "김주안"을 화면(특히 교외체험학습 앱 영역)에서 찾아서 클릭하는 JS
JS_CLICK_STUDENT = r"""
return (function() {
    var inst = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
        return ai.app && ai.app.id === "edu/sa/eds/eaa/ae/eds_eaaae01_m01";
    });
    if (!inst) return {error: "app not found"};
    
    var container = inst.getContainer();
    // 앱 컨테이너 내부의 모든 DOM 요소를 뒤집니다.
    // eXBuilder6 렌더링 트리에서 실제 DOM 요소를 얻기 위해 document.body에서 스캔하되,
    // 해당 앱의 uuid 등을 기준으로 하위 요소를 필터링할 수도 있습니다.
    // 여기서는 가장 직관적으로, 텍스트가 정확히 "김주안"인 엘리먼트를 찾습니다.
    
    var xpath = "//*[text()='김주안']";
    var evaluator = new XPathEvaluator();
    var result = evaluator.evaluate(xpath, document.documentElement, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
    var node = result.singleNodeValue;
    
    if (node) {
        node.click();
        return {ok: true, tagName: node.tagName, id: node.id, text: node.innerText};
    }
    
    // 대안: textContent 포함 여부로 검색
    var allElements = document.querySelectorAll('*');
    for (var i = 0; i < allElements.length; i++) {
        var el = allElements[i];
        if (el.innerText === "김주안" && (el.tagName === "SPAN" || el.tagName === "DIV" || el.tagName === "A" || el.tagName === "TD")) {
            el.click();
            return {ok: true, source: "querySelectorAll", tagName: el.tagName, id: el.id};
        }
    }
    
    return {error: "student element not found"};
})();
"""

res = driver.execute_script(JS_CLICK_STUDENT)
print(res)
