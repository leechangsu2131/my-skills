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

JS_FILL_FIRST_SAFE = """
var pop = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai && ai.app && ai.app.id.indexOf("p11") !== -1;
});
if (!pop) return {error: "Popup app (p11) not found"};

// 1. 왼쪽 일자 그리드에서 첫 번째 행(Index 0) 선택
var grdActYmd = pop.lookup("grdActYmd");
if (grdActYmd) {
    try {
        grdActYmd.selectRows([0]);
    } catch(e) {}
}

// 2. 오른쪽 폼 컴포넌트 찾아서 값 기입
var taCn = pop.lookup("gicSpeclActSpablMteCn");
var neHr = pop.lookup("gicComptHr");

if (taCn) {
    taCn.value = "봉사활동 소양교육";
    try {
        taCn.dispatchEvent(new cpr.events.CValueChangeEvent("value-change", {newValue: "봉사활동 소양교육"}));
    } catch(e) {}
}

if (neHr) {
    neHr.value = 1;
    try {
        neHr.dispatchEvent(new cpr.events.CValueChangeEvent("value-change", {newValue: 1}));
    } catch(e) {}
}

// 3. 학생 그리드 전체 선택 (안전한 다중 대체 로직)
var grdMain = pop.lookup("grdMain");
var checkMethodUsed = "none";
if (grdMain) {
    try {
        grdMain.checkAllRow();
        checkMethodUsed = "checkAllRow";
    } catch(e1) {
        try {
            var count = grdMain.getRowCount ? grdMain.getRowCount() : 18;
            for (var r=0; r<count; r++) {
                grdMain.checkRow(r, true);
            }
            checkMethodUsed = "checkRowLoop";
        } catch(e2) {
            var ds = pop.lookup("dsGicRec");
            if (ds) {
                var count = ds.getRowCount();
                for (var r=0; r<count; r++) {
                    ds.setValue(r, "chk", "Y");
                }
                checkMethodUsed = "datasetChkColumn";
            }
        }
    }
}

return {
    ok: true,
    checkMethodUsed: checkMethodUsed,
    actYmdValue: pop.lookup("dtGicActYmd") ? pop.lookup("dtGicActYmd").value : null,
    taCnValue: taCn ? taCn.value : null,
    neHrValue: neHr ? neHr.value : null
};
"""

try:
    res = driver.execute_script(JS_FILL_FIRST_SAFE)
    print("FILL RESULT:")
    print(json.dumps(res, ensure_ascii=False, indent=2))
except Exception as e:
    print("Error executing JS:", e)

# 화면 상태 확인용 스크린샷 캡처
driver.save_screenshot("scratch/screenshot.png")
print("Screenshot saved to scratch/screenshot.png")
driver.quit()
