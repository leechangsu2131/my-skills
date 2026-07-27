# -*- coding: utf-8 -*-
"""모든 nexacro 앱과 글로벌 범위의 데이터셋을 찾아 컬럼과 내용을 덤프합니다."""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import json

opts = Options()
opts.add_experimental_option("debuggerAddress", "localhost:9222")
driver = webdriver.Chrome(options=opts)
print(f"[연결] {driver.title}")

dump_js = """
function dumpAll() {
    var result = {
        global_datasets: [],
        apps: []
    };
    
    // 1. 글로벌 데이터셋 탐색
    try {
        var app = nexacro.getApplication();
        if (app && app._datasets) {
            for (var name in app._datasets) {
                var ds = app._datasets[name];
                if (ds) {
                    result.global_datasets.push({
                        id: name,
                        rows: ds.getRowCount ? ds.getRowCount() : -1
                    });
                }
            }
        }
    } catch(e) {
        result.global_err = e.message;
    }
    
    // 2. 실행 중인 모든 앱 인스턴스 탐색
    try {
        var insts = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        for (var i = 0; i < insts.length; i++) {
            var inst = insts[i];
            if (!inst || !inst.app) continue;
            
            var appInfo = {
                id: inst.app.id,
                datasets: [],
                components: []
            };
            
            // 모든 속성을 뒤져서 Dataset 객체나 Grid 객체 탐색
            for (var key in inst) {
                try {
                    var obj = inst[key];
                    if (!obj) continue;
                    
                    // Dataset 탐색
                    if (obj.getRowCount && typeof obj.getRowCount === 'function') {
                        var cols = [];
                        for (var c = 0; c < obj.getColCount(); c++) {
                            cols.push(obj.getColID(c));
                        }
                        var rowCount = obj.getRowCount();
                        var rows = [];
                        // 최대 20행까지만 내용 추출
                        for (var r = 0; r < Math.min(rowCount, 20); r++) {
                            var row = {};
                            for (var j = 0; j < cols.length; j++) {
                                row[cols[j]] = obj.getValue(r, cols[j]);
                            }
                            rows.push(row);
                        }
                        appInfo.datasets.push({
                            id: key,
                            rows: rowCount,
                            cols: cols,
                            data: rows
                        });
                    }
                    
                    // Component 탐색
                    if (obj.type && typeof obj.type === 'string') {
                        appInfo.components.push({
                            id: key,
                            type: obj.type
                        });
                    }
                } catch(e) {}
            }
            result.apps.push(appInfo);
        }
    } catch(e) {
        result.apps_err = e.message;
    }
    
    return result;
}
return dumpAll();
"""

res = driver.execute_script(dump_js)

# 파일로 결과 저장 및 출력
with open("scratch/neis_dataset_dump.json", "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=2)

print("\n--- 글로벌 데이터셋 ---")
for ds in res.get("global_datasets", []):
    print(f"  {ds['id']}: {ds['rows']} rows")

print("\n--- 앱 인스턴스 및 데이터셋 ---")
for app in res.get("apps", []):
    print(f"\n📂 앱 ID: {app['id']}")
    if app['datasets']:
        for ds in app['datasets']:
            print(f"  📊 데이터셋: {ds['id']} ({ds['rows']} rows)")
            print(f"    컬럼: {ds['cols']}")
            if ds['rows'] > 0:
                print("    데이터 샘플 (최대 5개):")
                for idx, row in enumerate(ds['data'][:5]):
                    print(f"      [{idx}] {row}")
    else:
        print("  (데이터셋 없음)")
        
    print(f"  🧩 컴포넌트 목록: {[c['id'] + '(' + c['type'] + ')' for c in app['components'][:10]]}")

driver.quit()
