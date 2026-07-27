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

# grdMain 사용 가능한 메서드 목록 확인
JS_DUMP_GRID_METHODS = """
var main = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce01_m07";
});
if (!main) return {error: "Main app not found"};

var grdMain = main.lookup("grdMain");
if (!grdMain) return {error: "grdMain not found"};

// 메서드 목록 (함수인 것만)
var methods = [];
for (var k in grdMain) {
    if (typeof grdMain[k] === "function" && k.indexOf("check") !== -1) {
        methods.push(k);
    }
}

return {methods: methods};
"""

try:
    res = driver.execute_script(JS_DUMP_GRID_METHODS)
    print("GRID CHECK METHODS:")
    print(json.dumps(res, ensure_ascii=False, indent=2))
except Exception as e:
    print("Error:", e)

driver.quit()
