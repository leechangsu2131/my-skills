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

JS_VERIFY = """
var main = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "edu/sa/eds/eaa/ae/eds_eaaae03_m01";
});
if (!main) return {error: "Main app not found"};

var btnSearch = main.lookup("btnSearch");
if (btnSearch) {
    btnSearch.click();
}

var ds = main.lookup("dsStdntListForAbe");
async function check() {
    await new Promise(r => setTimeout(r, 2000));
    var rows = [];
    for (var r=0; r<ds.getRowCount(); r++) {
        rows.push({
            stuFlnm: ds.getValue(r, "stuFlnm"),
            clsNo: ds.getValue(r, "clsNo"),
            eduActPrcsStsNm: ds.getValue(r, "eduActPrcsStsNm"),
            atrzStsNm: ds.getValue(r, "atrzStsNm")
        });
    }
    return rows;
}

window.__verifyResult = null;
check().then(function(res) {
    window.__verifyResult = res;
});
return "Verifying...";
"""

try:
    res = driver.execute_script(JS_VERIFY)
    print("Verify initiated:", res)
except Exception as e:
    print("Error:", e)

verify_result = None
for attempt in range(15):
    time.sleep(1.0)
    try:
        val = driver.execute_script("return window.__verifyResult;")
        if val is not None:
            verify_result = val
            break
    except: pass

print("VERIFICATION ABSENCE STATUS:")
print(json.dumps(verify_result, ensure_ascii=True, indent=2))

driver.save_screenshot("scratch/screenshot.png")
print("Screenshot saved.")
driver.quit()
