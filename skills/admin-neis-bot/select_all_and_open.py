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

JS_SELECT_AND_OPEN = """
// 1. 기존 팝업들 모두 닫기
var closedCount = 0;
var xButtons = document.querySelectorAll('.cl-dialog-close');
xButtons.forEach(function(btn) {
    try { btn.click(); closedCount++; } catch(e) {}
});

var main = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce01_m07";
});
if (!main) return {error: "Main app not found"};

// 메인의 모든 컨트롤들 뒤지기
var mainCtrls = [];
main.getContainer().getAllRecursiveChildren().forEach(function(c) {
    mainCtrls.push({id: c.id, type: c.type, visible: c.visible});
});

// 학생 그리드 찾기
var grdMain = main.lookup("grdMain") || main.lookup("grdStu") || main.lookup("grd1");
var selectResult = "";
if (grdMain) {
    try {
        // 모든 행 선택 시도
        grdMain.selectAllRows(true);
        selectResult = "selectAllRows succeeded";
    } catch(e) {
        selectResult = "selectAllRows failed: " + e.toString();
        // 데이터셋 체크 컬럼 설정 시도
        var ds = main.lookup("dsGicRec");
        if (ds) {
            var count = ds.getRowCount();
            for (var r=0; r<count; r++) {
                ds.setValue(r, "chk", "1"); // 또는 "Y" 또는 true
            }
            selectResult += " / Fallback ds GicRec chk column set";
        }
    }
}

// 2. 일괄등록 버튼 클릭
var btnBnde = main.lookup("btnBndeSave");
if (btnBnde) {
    btnBnde.click();
    return {ok: true, selectResult: selectResult, mainCtrls: mainCtrls};
}

return {error: "btnBndeSave not found", selectResult: selectResult};
"""

try:
    res = driver.execute_script(JS_SELECT_AND_OPEN)
    print("STEP 1 RESULT:")
    print(json.dumps(res, ensure_ascii=False, indent=2))
except Exception as e:
    print("Error executing JS:", e)

# 팝업 로딩 충분히 대기
print("Waiting 6 seconds for popup load...")
time.sleep(6.0)

JS_POPUP_CHECK = """
var pop = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai && ai.app && ai.app.id.indexOf("p11") !== -1;
});
if (!pop) return {error: "Popup app (p11) not found"};

var dataControls = [];
pop.getAllDataControls().forEach(function(ds) {
    var info = {id: ds.id, type: ds.type};
    if (ds.getRowCount) {
        info.rowCount = ds.getRowCount();
        var cols = ds.getColumnNames();
        var rows = [];
        var limit = Math.min(ds.getRowCount(), 10);
        for (var r=0; r<limit; r++) {
            var row = {};
            cols.forEach(function(c) {
                row[c] = ds.getValue(r, c);
            });
            rows.push(row);
        }
        info.data = rows;
    }
    dataControls.push(info);
});

return {
    appId: pop.app.id,
    dataControls: dataControls
};
"""

try:
    res_pop = driver.execute_script(JS_POPUP_CHECK)
    print("POPUP DATA DUMP:")
    print(json.dumps(res_pop, ensure_ascii=False, indent=2))
except Exception as e:
    print("Error dumping popup:", e)

driver.save_screenshot("scratch/screenshot.png")
print("Screenshot saved to scratch/screenshot.png")
driver.quit()
