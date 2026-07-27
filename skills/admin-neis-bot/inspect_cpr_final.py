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

JS_DUMP = """
var pop = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai && ai.app && ai.app.id.indexOf("p11") !== -1;
});
if (!pop) return {error: "Popup app (p11) not found"};

var dataControls = [];
if (pop.getAllDataControls) {
    pop.getAllDataControls().forEach(function(ds) {
        var info = {id: ds.id, type: ds.type};
        if (ds.getRowCount) {
            try {
                info.rowCount = ds.getRowCount();
                var cols = ds.getColumnNames();
                info.columns = cols;
                var rows = [];
                var limit = Math.min(ds.getRowCount(), 20);
                for (var r=0; r<limit; r++) {
                    var row = {};
                    cols.forEach(function(c) {
                        row[c] = ds.getValue(r, c);
                    });
                    rows.push(row);
                }
                info.data = rows;
            } catch(e) {
                info.error = e.toString();
            }
        }
        dataControls.push(info);
    });
}

// 팝업 내부의 UI 컴포넌트 목록
var ctrls = [];
if (pop.getChildren) {
    pop.getChildren().forEach(function(c) {
        ctrls.push({id: c.id, type: c.type, visible: c.visible});
    });
}

return {
    appId: pop.app.id,
    dataControls: dataControls,
    controls: ctrls
};
"""

try:
    res = driver.execute_script(JS_DUMP)
    print("SUCCESS_DUMP")
    print(json.dumps(res, ensure_ascii=False, indent=2))
except Exception as e:
    print("Error executing JS:", e)

driver.quit()
