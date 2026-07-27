#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""미상신 건을 체크하고 승인요청 버튼을 클릭하여 결재선 팝업을 띄우는 스크립트."""

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

# 1) 조회 실행
click_search_js = r"""
var inst = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "edu/sa/eds/eaa/ae/eds_eaaae01_m01";
});
if (!inst) return {error: "app not found"};
var btn = inst.lookup("btnSearch");
if (btn) btn.click();
return {ok: true};
"""
driver.execute_script(click_search_js)
time.sleep(2.0)

# 2) 접수+미상신 행 체크박스 체크
check_js = r"""
var inst = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "edu/sa/eds/eaa/ae/eds_eaaae01_m01";
});
if (!inst) return {error: "app not found"};
var grid = inst.lookup("grdMain");
var ds = inst.lookup("dsStdntListForAply");
if (!grid || !ds) return {error: "grid or ds not found"};

var checked = 0;

for (var r = 0; r < ds.getRowCount(); r++) {
    var status = ds.getValue(r, "eduActPrcsStsNm");
    var atrz = ds.getValue(r, "atrzStsNm");
    if (status === "접수" && atrz === "미상신") {
        ds.setValue(r, "chk", "1");
        checked++;
    } else {
        ds.setValue(r, "chk", "0");
    }
}
try { grid.redraw(); } catch(e) {}
return {checked: checked};
"""
res_check = driver.execute_script(check_js)
print("체크 완료 건수:", res_check)

if res_check.get("checked", 0) > 0:
    # 3) 승인요청 클릭
    click_req_js = r"""
    var inst = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
        return ai.app && ai.app.id === "edu/sa/eds/eaa/ae/eds_eaaae01_m01";
    });
    var btn = inst.lookup("btnUpdateCancel3"); // 승인요청
    if (btn) {
        btn.click();
        return {ok: true};
    }
    return {error: "btnUpdateCancel3 not found"};
    """
    res_req = driver.execute_script(click_req_js)
    print("승인요청 클릭 결과:", res_req)
    time.sleep(3.0)
else:
    print("승인요청할 건이 없습니다. 이미 상신되었거나 접수 상태가 아닙니다.")
