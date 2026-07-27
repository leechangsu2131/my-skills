#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""메인 셸 메뉴 검색창(siFindMenu)을 이용한 자동 메뉴 이동."""

import io, sys, time
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys

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

# 1) eXBuilder API로 siFindMenu에 값 입력 및 이벤트 실행
JS_SEARCH_MENU = r"""
return (function() {
    var inst = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
        return ai.app && ai.app.id === "app/com/main/Index";
    });
    if (!inst) return {error: "Index app not found"};
    
    var searchInput = inst.lookup("siFindMenu");
    if (!searchInput) return {error: "siFindMenu control not found"};
    
    // 값 설정 후 search 이벤트 발생 시도
    try {
        searchInput.value = "교외체험학습신청서관리";
        // eXBuilder6 searchinput 컨트롤은 보통 'search' 이벤트를 가지고 있습니다.
        if (typeof searchInput.dispatchEvent === 'function') {
            var event = new cpr.events.CUIEvent("search");
            searchInput.dispatchEvent(event);
            return {ok: true, method: "dispatchEvent"};
        }
    } catch(e) {
        return {error: e.message};
    }
    
    return {error: "search method fail"};
})();
"""

res = driver.execute_script(JS_SEARCH_MENU)
print("검색 시도 결과:", res)
time.sleep(2.0)

# 만약 API 레벨에서 검색이 실패했다면, DOM 레벨에서 input 태그를 찾아 텍스트 입력 후 엔터 입력
if res.get("error"):
    print("API 검색 실패로 DOM 레벨 검색 시도...")
    try:
        # searchinput 타입의 input 요소를 검색
        input_el = driver.find_element("css selector", "input.cl-searchinput-text, input[placeholder*='검색']")
        input_el.clear()
        input_el.send_keys("교외체험학습신청서관리")
        input_el.send_keys(Keys.ENTER)
        print("  -> DOM 입력 및 엔터 완료")
        time.sleep(3.0)
    except Exception as e:
        print("  -> DOM 검색창 조작 실패:", e)

# 검색 결과 팝업이 뜨거나 메뉴 리스트가 보일 때 해당 항목 클릭
JS_CLICK_SEARCH_RESULT = r"""
return (function() {
    // 화면에 나타난 검색결과 리스트에서 "교외체험학습신청서관리"가 들어간 행/텍스트를 클릭
    var all = document.querySelectorAll('*');
    for (var i = 0; i < all.length; i++) {
        var el = all[i];
        var text = (el.innerText || el.textContent || "").trim();
        if (text === "교외체험학습신청서관리" && (el.tagName === "SPAN" || el.tagName === "DIV" || el.tagName === "A")) {
            el.click();
            return {ok: true, clicked: text};
        }
    }
    return {error: "search result menu not found"};
})();
"""

res_click = driver.execute_script(JS_CLICK_SEARCH_RESULT)
print("검색 결과 클릭 시도:", res_click)
