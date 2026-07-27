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

JS_CLEANUP_DUPS = """
var main = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce01_m07";
});
if (!main) return {error: "Main app not found"};

var dsGicRec = main.lookup("dsGicRec");
var dsActYmd = main.lookup("dsActYmd");
var grdActYmd = main.lookup("grdActYmd");
var grdMain = main.lookup("grdMain");

// 확인 다이얼로그 클릭 헬퍼
function clickCprDialogOk() {
    var clicked = false;
    var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    apps.forEach(function(ai) {
        if (ai && ai.app && (ai.app.id.indexOf("confirm") !== -1 || ai.app.id.indexOf("alert") !== -1 || ai.app.id.indexOf("cmn") !== -1)) {
            try {
                var container = ai.getContainer ? ai.getContainer() : null;
                if (container && container.getAllRecursiveChildren) {
                    container.getAllRecursiveChildren().forEach(function(c) {
                        if (c && c.type === "button") {
                            var val = c.value || c.text || "";
                            if (val === "예" || val === "확인" || val.indexOf("확인") !== -1 || val.indexOf("예") !== -1) {
                                try { c.click(); clicked = true; } catch(e) {}
                            }
                        }
                    });
                }
            } catch(err) {}
        }
    });
    return clicked;
}

async function waitDialog(ms) {
    var start = Date.now();
    while (Date.now() - start < ms) {
        if (clickCprDialogOk()) return true;
        await new Promise(r => setTimeout(r, 300));
    }
    return false;
}

async function cleanupDate(idx) {
    grdActYmd.selectRows([idx]);
    await new Promise(r => setTimeout(r, 2000));
    
    var count = dsGicRec.getRowCount();
    var rowsToDelete = [];
    
    for (var r=0; r<count; r++) {
        var servActYn = dsGicRec.getValue(r, "servActYn");
        // 봉사활동 실적이 등록되어 있지 않은 행(N)을 삭제
        if (servActYn === "N" || servActYn === "" || !servActYn) {
            rowsToDelete.push(r);
        }
    }
    
    // 전체 체크 해제
    for (var r2=0; r2<count; r2++) {
        grdMain.setCheckRowIndex(r2, false);
    }
    
    // 삭제 대상 행 체크
    rowsToDelete.forEach(function(r3) {
        grdMain.setCheckRowIndex(r3, true);
    });
    grdMain.redraw();
    await new Promise(r => setTimeout(r, 500));
    
    var res = {dateIdx: idx, deleted: false, saved: false, initialCount: count, deleteTargetCount: rowsToDelete.length};
    
    var btnDelete = main.lookup("btnDelete");
    if (btnDelete && rowsToDelete.length > 0) {
        btnDelete.click();
        res.deleted = await waitDialog(2000);
        await new Promise(r => setTimeout(r, 1000));
        
        var btnSave = main.lookup("btnSave");
        if (btnSave) {
            btnSave.click();
            var confirmSaved = await waitDialog(3000);
            var alertSaved = await waitDialog(4000);
            res.saved = confirmSaved && alertSaved;
        }
    }
    return res;
}

async function runCleanup() {
    var logs = [];
    // 1. 7/9 일자 봉사활동 미설정 데이터 정리
    var r1 = await cleanupDate(0);
    logs.push(r1);
    await new Promise(r => setTimeout(r, 1500));
    
    // 2. 7/24 일자 봉사활동 미설정 데이터 정리
    var r2 = await cleanupDate(2);
    logs.push(r2);
    await new Promise(r => setTimeout(r, 1500));
    
    // 최종 재조회
    var btnSearch = main.lookup("btnSearch");
    if (btnSearch) {
        btnSearch.click();
    }
    
    return {status: "cleaned", logs: logs};
}

window.__cleanupResult = null;
runCleanup().then(function(res) {
    window.__cleanupResult = res;
}).catch(function(err) {
    window.__cleanupResult = {error: err.toString()};
});

return "Cleanup started...";
"""

try:
    res = driver.execute_script(JS_CLEANUP_DUPS)
    print("Cleanup sequence initiated:", res)
except Exception as e:
    print("Error:", e)

# 결과 대기 (최대 30초)
cleanup_result = None
for attempt in range(30):
    time.sleep(1.0)
    try:
        val = driver.execute_script("return window.__cleanupResult;")
        if val is not None:
            cleanup_result = val
            break
    except: pass

print("CLEANUP RESULTS:")
print(json.dumps(cleanup_result, ensure_ascii=True, indent=2))

driver.save_screenshot("scratch/screenshot.png")
print("Screenshot saved.")
driver.quit()
