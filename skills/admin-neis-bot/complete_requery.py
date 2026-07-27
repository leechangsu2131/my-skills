#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""팝업창들을 모두 닫고, 메인 화면 조회를 6초간 대기한 후 일괄등록 팝업을 다시 열어 데이터를 덤프하는 완결 조치 스크립트."""

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

JS_CLOSE_AND_REQUERY_COMPLETE = """
// 1. 모든 팝업창 닫기 (DOM '닫기' 텍스트 요소들 클릭)
var all = document.querySelectorAll('*');
var closedCount = 0;
for (var i = 0; i < all.length; i++) {
    var el = all[i];
    var text = (el.innerText || el.textContent || "").trim();
    if (text === "닫기" && (el.tagName === "SPAN" || el.tagName === "DIV" || el.tagName === "BUTTON")) {
        var target = el;
        for (var d=0; d<5; d++) {
            if (target.classList && (target.classList.contains("cl-button") || target.tagName === "BUTTON")) {
                break;
            }
            if (target.parentElement) target = target.parentElement;
            else break;
        }
        try {
            target.click();
            closedCount++;
        } catch(e) {}
    }
}

// X 버튼도 닫기
var xButtons = document.querySelectorAll('.cl-dialog-close');
xButtons.forEach(function(btn) {
    try {
        btn.click();
        closedCount++;
    } catch(e) {}
});

// 2. 메인 화면 조회 트리거
var main = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce01_m07";
});
if (!main) return {error: "els_sdlce01_m07 not found", closedCount: closedCount};

var btnSearch = main.lookup("btnSearch");
if (btnSearch) {
    btnSearch.click();
    return {ok: true, closedCount: closedCount, step: "query_triggered"};
}
return {error: "btnSearch not found on main", closedCount: closedCount};
"""

print("[run] 1단계: 모든 팝업 강제 차단 및 메인 조회 호출...")
res_1 = driver.execute_script(JS_CLOSE_AND_REQUERY_COMPLETE)
print("  결과:", res_1)

# 조회 충분히 로딩 대기
print("조회 로딩 7초 대기 중...")
time.sleep(7.0)

JS_REOPEN_BATCH = """
var main = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce01_m07";
});
if (!main) return {error: "els_sdlce01_m07 not found"};

// 동아리활동관리에 현재 로드된 활동일자 개수 확인
var dsActYmd = main.lookup("dsActYmd");
var mainYmdCount = dsActYmd ? dsActYmd.getRowCount() : 0;

var btnBnde = main.lookup("btnBndeSave"); // 일괄등록
if (btnBnde) {
    btnBnde.click();
    return {ok: true, mainYmdCount: mainYmdCount};
}
return {error: "btnBndeSave not found on main"};
"""

print("[run] 2단계: 일괄등록 버튼 클릭...")
res_2 = driver.execute_script(JS_REOPEN_BATCH)
print("  결과:", res_2)

# 팝업 로딩 대기
time.sleep(4.5)

# 신규 팝업 덤프
JS_POPUP_DUMP = """
var pop = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai && ai.app && ai.app.id.indexOf("p11") !== -1;
});
if (!pop) return {error: "Batch popup app not found after reopening"};

var datasets = [];
var dc = pop.getAllDataControls ? pop.getAllDataControls() : [];
dc.forEach(function(ds) {
    var cols = [];
    try { cols = ds.getColumnNames(); } catch(e) {}
    var rows = [];
    if (ds.getRowCount) {
        var limit = Math.min(ds.getRowCount(), 20);
        for (var r=0; r<limit; r++) {
            var row = {};
            cols.forEach(function(col) {
                row[col] = ds.getValue(r, col);
            });
            rows.push(row);
        }
    }
    datasets.push({id: ds.id, rowCount: ds.getRowCount(), data: rows});
});

return {
    appId: pop.app.id,
    datasets: datasets
};
"""

res_dump = driver.execute_script(JS_POPUP_DUMP)
print("3단계: 팝업 데이터셋 덤프 결과:")
print(json.dumps(res_dump, ensure_ascii=False, indent=2))

driver.save_screenshot("scratch/screenshot.png")
print("최종 스크린샷 저장 완료.")
driver.quit()
