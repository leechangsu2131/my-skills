#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""팝업을 닫고, 메인 화면에서 5초간 조회 로딩을 완전히 기다린 뒤 일괄등록 팝업을 다시 띄우는 복구 및 진단 스크립트."""

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

JS_RESET_AND_REQUERY = """
// 1. 현재 팝업이 떠 있으면 닫기
var pop = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai && ai.app && ai.app.id.indexOf("p11") !== -1;
});
if (pop) {
    var btnCancel = pop.lookup("btnCancel");
    if (btnCancel) btnCancel.click();
    else {
        // 닫기 텍스트 기반 클릭
        var c = pop.getContainer().getAllRecursiveChildren().find(function(el) {
            return (el.value || el.text || "").trim() === "닫기";
        });
        if (c) c.click();
    }
}

// 2. 메인 화면 찾기
var main = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce01_m07";
});
if (!main) return {error: "els_sdlce01_m07 not found"};

// 3. 메인 화면에서 조회 버튼 클릭
var btnSearch = main.lookup("btnSearch");
if (btnSearch) {
    btnSearch.click();
    return {ok: true, step: "requery_triggered"};
}
return {error: "btnSearch not found on main"};
"""

print("[run] 기존 팝업 닫고 메인 재조회 트리거...")
res_reset = driver.execute_script(JS_RESET_AND_REQUERY)
print("  결과:", res_reset)

if res_reset.get("error"):
    sys.exit(1)

# 조회 데이터 로딩 대기 (충분히 6초 대기)
print("조회 로딩 대기 중 (6초)...")
time.sleep(6.0)

JS_REOPEN_BATCH = """
var main = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce01_m07";
});
if (!main) return {error: "els_sdlce01_m07 not found"};

// 메인 화면 데이터셋 덤프하여 조회 완료 여부 확인
var dsGicRec = main.lookup("dsGicRec"); // 메인 그리드용
var mainRows = dsGicRec ? dsGicRec.getRowCount() : 0;

var btnBnde = main.lookup("btnBndeSave"); // 일괄등록
if (btnBnde) {
    btnBnde.click();
    return {ok: true, mainRows: mainRows};
}
return {error: "btnBndeSave not found on main"};
"""

print("[run] 일괄등록 버튼 다시 클릭...")
res_reopen = driver.execute_script(JS_REOPEN_BATCH)
print("  결과:", res_reopen)

# 팝업 로드 대기 (4초)
time.sleep(4.0)

JS_DUMP_POPUP_DATA = """
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

res_dump = driver.execute_script(JS_DUMP_POPUP_DATA)
dump_path = "scratch/neis_club_popup_reopen_diagnose.json"
with open(dump_path, "w", encoding="utf-8") as f:
    json.dump(res_dump, f, ensure_ascii=False, indent=2)
print(f"팝업 재진단 저장 성공: {dump_path}")

if "error" in res_dump:
    print("팝업 덤프 실패:", res_dump["error"])
else:
    print("성공적으로 일괄등록 창이 갱신되었습니다!")
    for ds in res_dump["datasets"]:
        print(f"  - ds: {ds['id']} (rows: {ds['rowCount']})")
        if ds["data"]:
            print(f"    * 데이터 샘플: {ds['data']}")

# 스크린샷 캡처
driver.save_screenshot("scratch/screenshot.png")
print("스크린샷 저장 완료.")
