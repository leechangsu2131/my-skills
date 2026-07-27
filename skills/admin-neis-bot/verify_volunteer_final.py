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

JS_VERIFY_VOLUNTEER = """
var main = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce01_m07";
});
if (!main) return {error: "Main app not found"};

var btnSearch = main.lookup("btnSearch");
if (btnSearch) {
    btnSearch.click();
}

var dsGicRec = main.lookup("dsGicRec");
var dsActYmd = main.lookup("dsActYmd");
var grdActYmd = main.lookup("grdActYmd");

async function checkAll() {
    await new Promise(r => setTimeout(r, 3000)); // 조회 대기
    
    var result = [];
    var dateCount = dsActYmd.getRowCount();
    
    for (var i=0; i<dateCount; i++) {
        var ymd = dsActYmd.getValue(i, "actYmd");
        var ymdNm = dsActYmd.getValue(i, "actYmdNm");
        
        grdActYmd.selectRows([i]);
        await new Promise(r => setTimeout(r, 2000)); // 날짜 변경 대기
        
        var count = dsGicRec.getRowCount();
        var rows = [];
        for (var r=0; r<count; r++) {
            rows.push({
                stuFlnm: dsGicRec.getValue(r, "stuFlnm"),
                speclActYmd: dsGicRec.getValue(r, "speclActYmd"),
                speclActSpablMteCn: dsGicRec.getValue(r, "speclActSpablMteCn"),
                servActYn: dsGicRec.getValue(r, "servActYn"),
                placeMngtInstNm: dsGicRec.getValue(r, "placeMngtInstNm"),
                comptHr: dsGicRec.getValue(r, "comptHr")
            });
        }
        
        result.push({
            ymd: ymd,
            ymdNm: ymdNm,
            totalRows: count,
            records: rows.slice(0, 3) // 상위 3명 샘플
        });
    }
    return result;
}

window.__verifyResult = null;
checkAll().then(function(res) {
    window.__verifyResult = res;
}).catch(function(err) {
    window.__verifyResult = {error: err.toString()};
});

return "Verification started...";
"""

try:
    res = driver.execute_script(JS_VERIFY_VOLUNTEER)
    print("Verification sequence initiated:", res)
except Exception as e:
    print("Error:", e)

# 결과 대기 (최대 30초)
verify_result = None
for attempt in range(30):
    time.sleep(1.0)
    try:
        val = driver.execute_script("return window.__verifyResult;")
        if val is not None:
            verify_result = val
            break
    except: pass

print("VERIFIED NEIS DATA SETTINGS:")
print(json.dumps(verify_result, ensure_ascii=True, indent=2))

driver.save_screenshot("scratch/screenshot.png")
print("Verification screenshot saved.")
driver.quit()
