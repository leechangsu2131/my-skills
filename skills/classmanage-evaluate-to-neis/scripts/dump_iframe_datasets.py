# -*- coding: utf-8 -*-
"""모든 창과 모든 iframe을 순차적으로 스위칭하며 eXBuilder6 데이터셋을 전수조사합니다."""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import json
import time

opts = Options()
opts.add_experimental_option("debuggerAddress", "localhost:9222")
driver = webdriver.Chrome(options=opts)
print(f"[연결] {driver.title}")

dump_js = """
function dumpApp() {
    var result = [];
    try {
        if (typeof cpr === 'undefined') return { error: 'cpr is undefined' };
        var insts = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        for (var i = 0; i < insts.length; i++) {
            var inst = insts[i];
            if (!inst || !inst.app) continue;
            
            var appInfo = {
                appId: inst.app.id,
                datasets: []
            };
            
            // 모든 데이터 컨트롤 가져오기
            if (typeof inst.getAllDataControls === 'function') {
                var controls = inst.getAllDataControls();
                for (var j = 0; j < controls.length; j++) {
                    var ctrl = controls[j];
                    if (ctrl && ctrl.type === 'dataset') {
                        var rowCount = ctrl.getRowCount();
                        var cols = ctrl.getColumnNames ? ctrl.getColumnNames() : [];
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
                }
            }
            result.push(appInfo);
        }
    } catch(e) {
        return { error: e.message };
    }
    return result;
}
return dumpApp();
"""

def decode_val(v):
    if isinstance(v, str):
        try:
            return v.encode('latin1').decode('euc-kr')
        except Exception:
            return v
    return v

all_results = []

handles = driver.window_handles
for handle in handles:
    driver.switch_to.window(handle)
    driver.switch_to.default_content()
    
    # 1. 메인 프레임 진단
    try:
        res = driver.execute_script(dump_js)
        if isinstance(res, list) and len(res) > 0:
            all_results.append({"window": driver.title, "frame": "main", "apps": res})
    except Exception as e:
        pass
        
    # 2. 모든 iframe 진단
    try:
        frames = driver.find_elements(By.TAG_NAME, "iframe")
        for idx, frame in enumerate(frames):
            fid = frame.get_attribute("id") or frame.get_attribute("name") or f"index_{idx}"
            try:
                driver.switch_to.default_content()
                driver.switch_to.frame(frame)
                res = driver.execute_script(dump_js)
                if isinstance(res, list) and len(res) > 0:
                    all_results.append({"window": driver.title, "frame": fid, "apps": res})
            except Exception:
                pass
    except Exception:
        pass

# 파일로 저장
with open("scratch/exbuilder_iframe_dump.json", "w", encoding="utf-8") as f:
    json.dump(all_results, f, ensure_ascii=False, indent=2)

print(f"\n✅ 진단 완료: {len(all_results)}개의 컨텍스트에서 데이터셋 발견")
for r in all_results:
    print(f"\n🖥️ Window: {r['window']} | Frame: {r['frame']}")
    for app in r['apps']:
        print(f"  📂 App: {app['appId']}")
        for ds in app['datasets']:
            print(f"    📊 Dataset: {ds['id']} ({ds['rows']} rows)")
            if ds['rows'] > 0:
                print("      첫 3개 행 데이터:")
                for r_idx, row in enumerate(ds['data'][:3]):
                    decoded = {k: decode_val(v) for k, v in row.items()}
                    print(f"        [{r_idx}] {decoded}")

driver.quit()
