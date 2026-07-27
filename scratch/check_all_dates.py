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

# 현재 화면의 dsGicRec 상세 내용 조회 (7/16 선택 상태)
JS_CHECK_EACH_DATE = """
var main = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce01_m07";
});
if (!main) return {error: "Main app not found"};

var dsGicRec = main.lookup("dsGicRec");
var dsActYmd = main.lookup("dsActYmd");
var grdActYmd = main.lookup("grdActYmd");

// 각 날짜별로 클릭해서 데이터 확인
var dateData = {};
var dateCount = dsActYmd ? dsActYmd.getRowCount() : 0;

for (var i=0; i<dateCount; i++) {
    var ymd = dsActYmd.getValue(i, "actYmd");
    var ymdNm = dsActYmd.getValue(i, "actYmdNm");
    
    // 날짜 선택 (그리드 행 선택)
    grdActYmd.selectRows([i]);
    
    // 잠깐 기다릴 수 없으므로, dsGicRec 현재 상태의 활동내용 컬럼 확인
    // (각 날짜 클릭 후 서버 요청이 필요하므로 비동기 필요)
    dateData[ymd] = {name: ymdNm, rowCount: dsGicRec.getRowCount()};
}

return {dateData: dateData, dateCount: dateCount};
"""

# 대신 async 접근으로 각 날짜 클릭 후 데이터 확인
JS_CHECK_DATES_ASYNC = """
var main = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce01_m07";
});
if (!main) return {error: "Main app not found"};

var dsGicRec = main.lookup("dsGicRec");
var dsActYmd = main.lookup("dsActYmd");
var grdActYmd = main.lookup("grdActYmd");
var grdMain = main.lookup("grdMain");

// 각 날짜에 대한 내용 확인을 위해 비동기로 순서대로 클릭
async function checkAllDates() {
    var result = [];
    var dateCount = dsActYmd.getRowCount();
    
    for (var i=0; i<dateCount; i++) {
        var ymd = dsActYmd.getValue(i, "actYmd");
        var ymdNm = dsActYmd.getValue(i, "actYmdNm");
        
        // 날짜 선택
        grdActYmd.selectRows([i]);
        await new Promise(r => setTimeout(r, 2000)); // 서버 조회 대기
        
        // 현재 dsGicRec 데이터 수집
        var rows = [];
        var count = dsGicRec.getRowCount();
        for (var r=0; r<Math.min(count, 3); r++) {
            rows.push({
                stuFlnm: dsGicRec.getValue(r, "stuFlnm"),
                speclActYmd: dsGicRec.getValue(r, "speclActYmd"),
                speclActSpablMteCn: dsGicRec.getValue(r, "speclActSpablMteCn"),
                comptHr: dsGicRec.getValue(r, "comptHr"),
                speclActComptSeq: dsGicRec.getValue(r, "speclActComptSeq")
            });
        }
        
        result.push({
            ymd: ymd,
            ymdNm: ymdNm,
            totalRows: count,
            sample: rows
        });
    }
    
    return result;
}

window.__checkResult = null;
checkAllDates().then(function(res) {
    window.__checkResult = res;
}).catch(function(err) {
    window.__checkResult = {error: err.toString()};
});

return "Checking all dates...";
"""

try:
    res = driver.execute_script(JS_CHECK_DATES_ASYNC)
    print("Started:", res)
except Exception as e:
    print("Error:", e)

# 비동기 완료 대기 (최대 30초, 3일자 × 2초 × 여유)
check_result = None
for attempt in range(30):
    time.sleep(1.0)
    try:
        val = driver.execute_script("return window.__checkResult;")
        if val is not None:
            check_result = val
            break
    except: pass

print("DATE CHECK RESULTS:")
print(json.dumps(check_result, ensure_ascii=False, indent=2))

driver.save_screenshot("scratch/screenshot.png")
print("Screenshot saved.")
driver.quit()
