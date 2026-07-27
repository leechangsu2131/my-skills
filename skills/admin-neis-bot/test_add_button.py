#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""일자추가(직접입력) 버튼을 클릭한 후 팝업 내부 상태와 데이터셋 변화를 진단하는 스크립트."""

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

# 1) btnYmdAdd 클릭 실행
JS_CLICK_ADD = """
var pop = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai && ai.app && ai.app.id.indexOf("p11") !== -1;
});
if (!pop) return {error: "Batch popup app not found"};

var btnAdd = pop.lookup("btnYmdAdd");
if (!btnAdd) return {error: "btnYmdAdd not found"};

btnAdd.click();
return {ok: true};
"""

print("[run] btnYmdAdd ([일자추가(직접입력)]) 클릭...")
res_click = driver.execute_script(JS_CLICK_ADD)
print("  결과:", res_click)
time.sleep(3.0) # 혹시 신규 모달 팝업이 뜰 수 있으므로 로딩 대기

# 2) 팝업 상태 재덤프 (신규 팝업 앱이 떴는지 아니면 기존 앱 내부 구조가 바뀌었는지 체크)
JS_CHECK_APPS = """
var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
var appList = [];
instances.forEach(function(ai, idx) {
    if (!ai || !ai.app) return;
    var dsList = [];
    var dc = ai.getAllDataControls ? ai.getAllDataControls() : [];
    dc.forEach(function(ds) {
        var cols = [];
        try { cols = ds.getColumnNames(); } catch(e) {}
        
        var rows = [];
        if (ds.getRowCount) {
            var limit = Math.min(ds.getRowCount(), 10);
            for (var r=0; r<limit; r++) {
                var row = {};
                cols.forEach(function(col) {
                    row[col] = ds.getValue(r, col);
                });
                rows.push(row);
            }
        }
        dsList.push({id: ds.id, rowCount: ds.getRowCount(), cols: cols, data: rows});
    });
    
    appList.push({
        idx: idx,
        appId: ai.app.id,
        title: ai.title || "",
        datasets: dsList
    });
});
return appList;
"""

res_apps = driver.execute_script(JS_CHECK_APPS)
dump_path = "scratch/neis_club_add_diagnose.json"
with open(dump_path, "w", encoding="utf-8") as f:
    json.dump(res_apps, f, ensure_ascii=False, indent=2)
print(f"추가 후 앱 목록 저장: {dump_path}")

# 콘솔 요약 출력
print("\n[현재 활성 앱 목록 요약]")
for app in res_apps:
    print(f"AppId: {app['appId']} | Title: '{app['title']}'")
    for ds in app["datasets"]:
        print(f"  - ds: {ds['id']} (rows: {ds['rowCount']})")
        if ds["data"]:
            print(f"    * 1행 데이터: {ds['data'][0]}")

# 스크린샷 갱신
driver.save_screenshot("scratch/screenshot.png")
print("스크린샷 갱신 완료.")
