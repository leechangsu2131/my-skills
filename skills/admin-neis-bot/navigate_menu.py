#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""교외체험학습신청서관리 메뉴를 자동으로 찾아가서 클릭/로딩하는 스크립트."""

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

def click_menu_item(name: str) -> bool:
    js = r"""
    var text = "TARGET_NAME";
    var all = document.querySelectorAll('*');
    for (var i = 0; i < all.length; i++) {
        var el = all[i];
        var val = (el.innerText || el.textContent || "").trim();
        if (val === text && (el.tagName === "SPAN" || el.tagName === "DIV" || el.tagName === "A" || el.tagName === "TD")) {
            el.click();
            return {ok: true, text: text, tagName: el.tagName};
        }
    }
    // 부분 매칭
    for (var i = 0; i < all.length; i++) {
        var el = all[i];
        var val = (el.innerText || el.textContent || "").trim();
        if (val.indexOf(text) >= 0 && (el.tagName === "SPAN" || el.tagName === "DIV" || el.tagName === "A")) {
            if (el.children.length <= 1) {
                el.click();
                return {ok: true, text: text, partial: true, tagName: el.tagName};
            }
        }
    }
    return {error: "not found"};
    """.replace("TARGET_NAME", name)
    
    res = driver.execute_script(js)
    if res.get("ok"):
        print(f"  -> '{name}' 클릭 성공 ({res.get('tagName')})")
        return True
    else:
        print(f"  -> '{name}' 찾을 수 없음, 재시도...")
        return False

# 메뉴 자동 클릭 시퀀스
steps = ["학급담임", "교육활동신청관리", "교외체험학습관리", "교외체험학습신청서관리"]

print("=== 메뉴 자동 이동 시퀀스 시작 ===")
for step in steps:
    success = False
    for attempt in range(3):
        if click_menu_item(step):
            success = True
            time.sleep(1.5)
            break
        time.sleep(1.0)
    if not success:
        print(f"[경고] '{step}' 단계에서 클릭 실패. 진행을 계속 시도합니다.")

print("=== 4초 대기 (로딩)... ===")
time.sleep(4.0)

# 최종 로드 여부 검증
app_check_js = r"""
var inst = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "edu/sa/eds/eaa/ae/eds_eaaae01_m01";
});
return inst ? {ok: true, appId: inst.app.id} : {ok: false};
"""
check = driver.execute_script(app_check_js)
if check.get("ok"):
    print(f"[OK] 교외체험학습 앱 발견 성공: {check.get('appId')}")
else:
    print("[경고] 화면 이동이 완료되지 않았거나 백그라운드 탭에 있을 수 있습니다.")
