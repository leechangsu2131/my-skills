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

JS_CLICK_CLOSE_BTN = """
var pop = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai && ai.app && ai.app.id.indexOf("p11") !== -1;
});
if (!pop) return {error: "Popup app (p11) not found"};

var btnClose = pop.lookup("btnClose");
if (btnClose) {
    try {
        btnClose.click(); // eXbuilder6 버튼 API 클릭
        return {success: true, msg: "btnClose.click() executed"};
    } catch(e) {
        return {success: false, error: e.toString()};
    }
}

return {success: false, error: "btnClose control not found"};
"""

try:
    res = driver.execute_script(JS_CLICK_CLOSE_BTN)
    print("Close button click result:", res)
except Exception as e:
    print("Error:", e)

# 2초 대기하여 팝업이 닫혔는지 확인하고 메인 화면 새로 조회
time.sleep(2.0)

JS_MAIN_REFRESH = """
var main = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce01_m07";
});
if (main) {
    var btnSearch = main.lookup("btnSearch");
    if (btnSearch) {
        btnSearch.click();
        return "Main search clicked";
    }
}
return "Main app not found";
"""

try:
    res2 = driver.execute_script(JS_MAIN_REFRESH)
    print("Main search result:", res2)
except Exception as e:
    print("Error:", e)

# 메인 로딩 대기 (6초)
time.sleep(6.0)

JS_VERIFY_DATA = """
var main = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce01_m07";
});
if (!main) return {error: "Main app not found"};

var dsGicRec = main.lookup("dsGicRec");
var rows = [];
if (dsGicRec) {
    var count = dsGicRec.getRowCount();
    var limit = Math.min(count, 50);
    for (var r=0; r<limit; r++) {
        rows.push({
            stuFlnm: dsGicRec.getValue(r, "stuFlnm"),
            speclActYmd: dsGicRec.getValue(r, "speclActYmd"),
            speclActSpablMteCn: dsGicRec.getValue(r, "speclActSpablMteCn"),
            comptHr: dsGicRec.getValue(r, "comptHr")
        });
    }
}
return {totalRows: dsGicRec ? dsGicRec.getRowCount() : 0, sample: rows};
"""

try:
    res3 = driver.execute_script(JS_VERIFY_DATA)
    print("VERIFIED NEIS DATA:")
    print(json.dumps(res3, ensure_ascii=False, indent=2))
except Exception as e:
    print("Error getting final verified data:", e)

driver.save_screenshot("scratch/screenshot.png")
print("Verification screenshot saved.")
driver.quit()
