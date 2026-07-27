#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""동아리활동 일괄등록 팝업을 열고 내부 컨트롤 구조를 정밀하게 덤프하는 진단 스크립트."""

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

# 1) 동아리활동관리 탭 활성화 및 조회 클릭, 그 후 일괄등록 버튼 클릭
JS_OPEN_BATCH_POPUP = """
var inst = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce01_m07";
});
if (!inst) return {error: "els_sdlce01_m07 not found"};

// 탭 활성화 시뮬레이션은 Python 단에서 trigger하는게 더 확실
var btnSearch = inst.lookup("btnSearch");
if (btnSearch) btnSearch.click();

var btnBnde = inst.lookup("btnBndeSave"); // 일괄등록
if (btnBnde) {
    btnBnde.click();
    return {ok: true};
}
return {error: "btnBndeSave not found"};
"""

print("[run] 동아리활동관리 탭 조회 후 일괄등록 클릭...")
res_open = driver.execute_script(JS_OPEN_BATCH_POPUP)
print("  결과:", res_open)
time.sleep(3.0) # 팝업 뜨는 대기 시간

# 2) 팝업 앱 덤프
JS_DUMP_POPUP = """
var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
var pop = instances.find(function(ai) {
    return ai && ai.app && (ai.app.id.indexOf("p11") !== -1 || ai.app.id.indexOf("els_sdlce00_p11") !== -1);
});
if (!pop) return {error: "Batch popup app not found"};

var ctrls = [];
pop.getContainer().getAllRecursiveChildren().forEach(function(c) {
    ctrls.push({
        id: c.id || "",
        type: c.type || "",
        val: c.value || c.text || "",
        fieldLabel: c.fieldLabel || ""
    });
});

var datasets = [];
var dc = pop.getAllDataControls ? pop.getAllDataControls() : [];
dc.forEach(function(ds) {
    var cols = [];
    try {
        if (ds.getColumnNames) cols = ds.getColumnNames();
    } catch(e) {}
    
    // 데이터셋에 들어있는 현재 데이터 덤프
    var rows = [];
    if (ds.getRowCount) {
        var limit = Math.min(ds.getRowCount(), 20);
        for (var r = 0; r < limit; r++) {
            var row = {};
            cols.forEach(function(col) {
                row[col] = ds.getValue(r, col);
            });
            rows.push(row);
        }
    }
    datasets.push({id: ds.id || "", rowCount: ds.getRowCount(), cols: cols, data: rows});
});

return {
    appId: pop.app.id,
    controls: ctrls,
    datasets: datasets
};
"""

res_popup = driver.execute_script(JS_DUMP_POPUP)
dump_path = "scratch/neis_club_popup_diagnose.json"
with open(dump_path, "w", encoding="utf-8") as f:
    json.dump(res_popup, f, ensure_ascii=False, indent=2)
print(f"일괄등록 팝업 진단 저장 성공: {dump_path}")

if "error" in res_popup:
    print("팝업 진단 실패:", res_popup["error"])
else:
    print(f"팝업 앱 ID: {res_popup['appId']}")
    print("데이터셋 목록:")
    for ds in res_popup["datasets"]:
        print(f"  - ds: {ds['id']} (rows: {ds['rowCount']}) | cols: {ds['cols']}")
        if ds["data"]:
            print(f"    * 1행 데이터: {ds['data'][0]}")
    print("콤보박스 및 주요 컨트롤 목록:")
    for c in res_popup["controls"]:
        if c["type"] in ["combobox", "grid", "checkbox", "button"] or c["id"]:
            print(f"  - ID: '{c['id']}' | Type: '{c['type']}' | Label: '{c['fieldLabel']}' | Val: '{c['val']}'")
