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

JS_REFRESH_AND_VERIFY = """
var main = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce01_m07";
});
if (!main) return {error: "Main app not found"};

// 조회 버튼 클릭
var btnSearch = main.lookup("btnSearch");
if (btnSearch) {
    btnSearch.click();
}

return "Refresh initiated...";
"""

try:
    res = driver.execute_script(JS_REFRESH_AND_VERIFY)
    print("Refresh result:", res)
except Exception as e:
    print("Error launching refresh:", e)

# 6초 대기하여 로딩 완료 대기
time.sleep(6.0)

JS_DUMP_VERIFY = """
var main = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce01_m07";
});
if (!main) return {error: "Main app not found"};

var dsGicRec = main.lookup("dsGicRec");
var rows = [];
if (dsGicRec) {
    var limit = Math.min(dsGicRec.getRowCount(), 30);
    var cols = dsGicRec.getColumnNames();
    for (var r=0; r<limit; r++) {
        var row = {};
        row.stuFlnm = dsGicRec.getValue(r, "stuFlnm");
        row.speclActYmd = dsGicRec.getValue(r, "speclActYmd");
        row.speclActSpablMteCn = dsGicRec.getValue(r, "speclActSpablMteCn");
        row.comptHr = dsGicRec.getValue(r, "comptHr");
        rows.push(row);
    }
}

return {
    rowCount: dsGicRec ? dsGicRec.getRowCount() : 0,
    sample: rows
};
"""

try:
    res2 = driver.execute_script(JS_DUMP_VERIFY)
    print("VERIFICATION DUMP:")
    print(json.dumps(res2, ensure_ascii=False, indent=2))
except Exception as e:
    print("Error verifying data:", e)

driver.save_screenshot("scratch/screenshot.png")
print("Verification screenshot saved.")
driver.quit()
