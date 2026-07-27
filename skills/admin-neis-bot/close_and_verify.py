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

JS_CLOSE_AND_REFRESH = """
var pop = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai && ai.app && ai.app.id.indexOf("p11") !== -1;
});
if (pop) {
    try {
        // eXbuilder6 팝업 인스턴스 자체 닫기
        pop.close();
    } catch(e) {
        // fallback: X 닫기 단추 클릭
        var xBtn = document.querySelector('.cl-dialog-close');
        if (xBtn) xBtn.click();
    }
}

// 메인 화면 조회
var main = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce01_m07";
});
if (main) {
    var btnSearch = main.lookup("btnSearch");
    if (btnSearch) {
        btnSearch.click();
    }
}

return {popupClosed: !pop || pop.isClosed, hasMain: !!main};
"""

try:
    res = driver.execute_script(JS_CLOSE_AND_REFRESH)
    print("Close and Refresh result:", res)
except Exception as e:
    print("Error:", e)

# 메인 조회 결과 완료 대기 (6초)
print("Waiting 6 seconds for main search loading...")
time.sleep(6.0)

JS_FINAL_VERIFY = """
var main = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce01_m07";
});
if (!main) return {error: "Main app not found"};

var dsGicRec = main.lookup("dsGicRec");
var rows = [];
if (dsGicRec) {
    var count = dsGicRec.getRowCount();
    var limit = Math.min(count, 50);
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
    totalRows: dsGicRec ? dsGicRec.getRowCount() : 0,
    sample: rows
};
"""

try:
    res2 = driver.execute_script(JS_FINAL_VERIFY)
    print("FINAL VERIFIED DATA:")
    # 유니코드 바인딩 디버그를 포함해 깔끔하게 출력
    print(json.dumps(res2, ensure_ascii=False, indent=2))
except Exception as e:
    print("Error during final verification:", e)

driver.save_screenshot("scratch/screenshot.png")
print("Verification screenshot saved.")
driver.quit()
