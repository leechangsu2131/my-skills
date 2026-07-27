import io, sys, time, json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

driver_path = r"C:\Users\lee21\.cache\selenium\chromedriver\win64\150.0.7871.115\chromedriver.exe"
service = Service(executable_path=driver_path)

opts = Options()
opts.add_experimental_option("debuggerAddress", "localhost:9222")
driver = webdriver.Chrome(service=service, options=opts)

# Find target window
target_handle = None
for handle in driver.window_handles:
    driver.switch_to.window(handle)
    driver.switch_to.default_content()
    try:
        if driver.execute_script("return typeof cpr !== 'undefined';") and "vpn" not in driver.current_url.lower():
            target_handle = handle
            break
    except: pass

if not target_handle:
    print("Error: Target window not found.")
    driver.quit()
    sys.exit(1)

# 이 화면은 동아리닥임 화면 (els_sdlce01_m07과 다른 화면)
# 현재 실행 중인 앱 인스턴스와 데이터셋 구조 파악
JS_DIAGNOSE_ALL = """
var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
var result = apps.map(function(ai) {
    var datasets = [];
    try {
        ai.getAllDataControls().forEach(function(ds) {
            var rows = [];
            if (ds.getRowCount && ds.getRowCount() > 0) {
                var limit = Math.min(ds.getRowCount(), 5);
                for (var r=0; r<limit; r++) {
                    try {
                        var row = {};
                        var cols = ds.getColumnNames ? ds.getColumnNames() : [];
                        cols.slice(0, 15).forEach(function(c) {
                            row[c] = ds.getValue(r, c);
                        });
                        rows.push(row);
                    } catch(e) {}
                }
            }
            datasets.push({
                id: ds.id,
                type: ds.type,
                rowCount: ds.getRowCount ? ds.getRowCount() : null,
                sample: rows
            });
        });
    } catch(e) {}
    return {
        appId: ai.app ? ai.app.id : null,
        datasets: datasets
    };
});
return result;
"""

try:
    res = driver.execute_script(JS_DIAGNOSE_ALL)
    print("ALL APPS & DATASETS:")
    print(json.dumps(res, ensure_ascii=False, indent=2))
except Exception as e:
    print("Error:", e)

driver.quit()
