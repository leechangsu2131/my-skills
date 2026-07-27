#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""팝업창 내의 버튼 객체들을 정확하게 식별하고, 일자추가 버튼을 강제 트리거하는 디버깅 스크립트."""

import io, sys, time, json
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

JS_DIAGNOSE_POPUP_CONTROLS = """
var pop = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai && ai.app && (ai.app.id.indexOf("p11") !== -1 || ai.app.id.indexOf("els_sdlce00_p11") !== -1);
});
if (!pop) {
    // 혹시 다른 앱 ID인지 탐색
    var all = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var apps = all.map(function(ai) { return ai.app ? ai.app.id : "null"; });
    return {error: "Popup app not found", runningApps: apps};
}

var container = pop.getContainer();
var buttons = [];
container.getAllRecursiveChildren().forEach(function(c) {
    if (c.type === "button" || (c.value && c.value.indexOf("일자추가") !== -1)) {
        buttons.push({
            id: c.id || "",
            type: c.type || "",
            val: c.value || c.text || "",
            visible: c.visible
        });
    }
});

// btnYmdAdd 버튼 찾기
var targetBtn = pop.lookup("btnYmdAdd");
var clickResult = "not_attempted";
if (targetBtn) {
    try {
        targetBtn.click();
        clickResult = "clicked_successfully";
    } catch(e) {
        clickResult = "click_failed: " + e.message;
    }
} else {
    // 텍스트 기반으로 찾아서 클릭 시도
    var foundBtn = container.getAllRecursiveChildren().find(function(c) {
        return (c.value || c.text || "").indexOf("일자추가") !== -1;
    });
    if (foundBtn) {
        try {
            foundBtn.click();
            clickResult = "clicked_by_text_successfully: " + foundBtn.id;
        } catch(e) {
            clickResult = "click_by_text_failed: " + e.message;
        }
    } else {
        clickResult = "button_not_found_by_any_means";
    }
}

return {
    appId: pop.app.id,
    buttons: buttons,
    clickResult: clickResult
};
"""

print("[run] 팝업 버튼 디버그 및 클릭 트리거 실행...")
res = driver.execute_script(JS_DIAGNOSE_POPUP_CONTROLS)
print("결과:")
print(json.dumps(res, ensure_ascii=False, indent=2))

time.sleep(3.0)
driver.save_screenshot("scratch/screenshot.png")
print("스크린샷 업데이트 완료.")
