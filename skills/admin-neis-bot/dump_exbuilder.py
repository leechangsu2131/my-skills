# -*- coding: utf-8 -*-
"""eXBuilder6 getAllDataControls() API를 이용해 모든 데이터셋과 데이터를 추출합니다."""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import json

opts = Options()
opts.add_experimental_option("debuggerAddress", "localhost:9222")
driver = webdriver.Chrome(options=opts)
print(f"[연결] {driver.title}")

dump_js = """
function dumpAllExBuilder() {
    var result = {
        apps: []
    };
    
    try {
        var insts = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        for (var i = 0; i < insts.length; i++) {
            var inst = insts[i];
            if (!inst || !inst.app) continue;
            
            var appInfo = {
                id: inst.app.id,
                datasets: [],
                datamaps: [],
                components: []
            };
            
            // eXBuilder6 getAllDataControls API 사용
            try {
                if (typeof inst.getAllDataControls === 'function') {
                    var controls = inst.getAllDataControls();
                    for (var j = 0; j < controls.length; j++) {
                        var ctrl = controls[j];
                        if (!ctrl) continue;
                        
                        // Dataset인 경우
                        if (ctrl.type === 'dataset') {
                            var rowCount = ctrl.getRowCount();
                            var cols = ctrl.getColumnNames ? ctrl.getColumnNames() : [];
                            if (cols.length === 0 && ctrl.getColCount) {
                                for (var c = 0; c < ctrl.getColCount(); c++) {
                                    cols.push(ctrl.getColID(c));
                                }
                            }
                            
                            var rows = [];
                            for (var r = 0; r < rowCount; r++) {
                                var row = {};
                                for (var cc = 0; cc < cols.length; cc++) {
                                    row[cols[cc]] = ctrl.getValue(r, cols[cc]);
                                }
                                rows.push(row);
                            }
                            
                            appInfo.datasets.push({
                                id: ctrl.id,
                                rows: rowCount,
                                cols: cols,
                                data: rows
                            });
                        }
                        // Datamap인 경우
                        else if (ctrl.type === 'datamap') {
                            appInfo.datamaps.push({
                                id: ctrl.id,
                                data: ctrl.getDatas ? ctrl.getDatas() : null
                            });
                        }
                    }
                }
            } catch(e) {
                appInfo.data_err = e.message;
            }
            
            result.apps.push(appInfo);
        }
    } catch(e) {
        result.err = e.message;
    }
    
    return result;
}
return dumpAllExBuilder();
"""

res = driver.execute_script(dump_js)

# 파일로 저장
with open("scratch/exbuilder_dataset_dump.json", "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=2)

print("\n--- eXBuilder6 앱별 데이터셋 검색 결과 ---")
for app in res.get("apps", []):
    print(f"\n📂 앱 ID: {app['id']}")
    if app.get("data_err"):
        print(f"  ⚠️ 오류: {app['data_err']}")
    
    if app['datasets']:
        for ds in app['datasets']:
            print(f"  📊 [Dataset] {ds['id']} ({ds['rows']} rows)")
            print(f"    컬럼: {ds['cols']}")
            if ds['rows'] > 0:
                print("    데이터 샘플:")
                # 한글 깨짐 디코딩 시도
                for idx, row in enumerate(ds['data']):
                    decoded_row = {}
                    for k, v in row.items():
                        if isinstance(v, str):
                            try:
                                decoded_row[k] = v.encode('latin1').decode('euc-kr')
                            except Exception:
                                decoded_row[k] = v
                        else:
                            decoded_row[k] = v
                    print(f"      [{idx}] {decoded_row}")
    else:
        print("  (Dataset 없음)")

    if app['datamaps']:
        for dm in app['datamaps']:
            print(f"  🗺️ [Datamap] {dm['id']}: {dm['data']}")

driver.quit()
