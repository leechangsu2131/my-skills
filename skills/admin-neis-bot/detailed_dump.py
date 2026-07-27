import io, sys, time, json, os
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

print(f"Connected to: {driver.title}")

JS_DETAILED_DUMP = """
var result = {};

// 1. 메인 앱 찾기 및 덤프
var main = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce01_m07";
});
if (main) {
    var mainDCs = [];
    main.getAllDataControls().forEach(function(ds) {
        var info = {id: ds.id, type: ds.type};
        if (ds.getRowCount) {
            info.rowCount = ds.getRowCount();
            var cols = ds.getColumnNames();
            var rows = [];
            var limit = Math.min(ds.getRowCount(), 50);
            for (var r=0; r<limit; r++) {
                var row = {};
                cols.forEach(function(c) {
                    row[c] = ds.getValue(r, c);
                });
                rows.push(row);
            }
            info.data = rows;
        }
        mainDCs.push(info);
    });
    result.main = {
        appId: main.app.id,
        dataControls: mainDCs
    };
}

// 2. 팝업 앱 찾기 및 덤프
var pop = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai && ai.app && ai.app.id.indexOf("p11") !== -1;
});
if (pop) {
    var popDCs = [];
    pop.getAllDataControls().forEach(function(ds) {
        var info = {id: ds.id, type: ds.type};
        if (ds.getRowCount) {
            info.rowCount = ds.getRowCount();
            var cols = ds.getColumnNames();
            var rows = [];
            var limit = Math.min(ds.getRowCount(), 50);
            for (var r=0; r<limit; r++) {
                var row = {};
                cols.forEach(function(c) {
                    row[c] = ds.getValue(r, c);
                });
                rows.push(row);
            }
            info.data = rows;
        }
        popDCs.push(info);
    });
    
    var popCtrls = [];
    pop.getContainer().getAllRecursiveChildren().forEach(function(ctrl) {
        var cinfo = {id: ctrl.id, type: ctrl.type, visible: ctrl.visible};
        if (ctrl.value !== undefined) cinfo.value = ctrl.value;
        if (ctrl.text !== undefined) cinfo.text = ctrl.text;
        popCtrls.push(cinfo);
    });
    
    result.popup = {
        appId: pop.app.id,
        dataControls: popDCs,
        controls: popCtrls
    };
}

return result;
"""

try:
    res = driver.execute_script(JS_DETAILED_DUMP)
    os.makedirs("scratch", exist_ok=True)
    with open("scratch/detailed_dump.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print("SUCCESS: Detailed dump saved to scratch/detailed_dump.json")
except Exception as e:
    print("Error executing JS:", e)

driver.quit()
