import io, sys, time, json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

driver_path = r"C:\Users\cache\selenium\chromedriver\win64\150.0.7871.115\chromedriver.exe"
# 올바른 드라이버 캐시 경로 설정
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

JS_UPDATE_CONTENTS = """
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

async function updateAll() {
    var logs = [];
    var btnSave = main.lookup("btnSave");
    
    // -------------------------------------------------------------------------
    // 1. 7/9 일자 업데이트 (봉사활동 소양교육)
    // -------------------------------------------------------------------------
    grdActYmd.selectRows([0]);
    await new Promise(r => setTimeout(r, 2000));
    
    var count0 = dsGicRec.getRowCount();
    for (var r=0; r<count0; r++) {
        dsGicRec.setValue(r, "speclActSpablMteCn", "봉사활동 소양교육");
    }
    grdMain.redraw();
    if (btnSave) {
        btnSave.click();
        var c1 = await waitDialog(3000);
        var a1 = await waitDialog(4000);
        logs.push({date: "7/9", confirm: c1, alert: a1});
    }
    await new Promise(r => setTimeout(r, 1500));

    // -------------------------------------------------------------------------
    // 2. 7/16 일자 업데이트 (2시간 개별 기입)
    // -------------------------------------------------------------------------
    grdActYmd.selectRows([1]);
    await new Promise(r => setTimeout(r, 2000));
    
    var count1 = dsGicRec.getRowCount();
    var seen = {}; // 학생별 등장 횟수 트래킹
    for (var r=0; r<count1; r++) {
        var stuNo = dsGicRec.getValue(r, "stuInvlNo");
        if (!seen[stuNo]) {
            seen[stuNo] = 1;
            dsGicRec.setValue(r, "speclActSpablMteCn", "도서관에서 지켜야할 예절 토의하기");
        } else {
            seen[stuNo] += 1;
            dsGicRec.setValue(r, "speclActSpablMteCn", "내가 좋아하는 책 친구들에게 소개하기");
        }
    }
    grdMain.redraw();
    if (btnSave) {
        btnSave.click();
        var c2 = await waitDialog(3000);
        var a2 = await waitDialog(4000);
        logs.push({date: "7/16", confirm: c2, alert: a2});
    }
    await new Promise(r => setTimeout(r, 1500));

    // -------------------------------------------------------------------------
    // 3. 7/24 일자 업데이트 (독서 캠페인 - 독서 활동 홍보 포스터 만들기)
    // -------------------------------------------------------------------------
    grdActYmd.selectRows([2]);
    await new Promise(r => setTimeout(r, 2000));
    
    var count2 = dsGicRec.getRowCount();
    for (var r=0; r<count2; r++) {
        dsGicRec.setValue(r, "speclActSpablMteCn", "독서 캠페인 - 독서 활동 홍보 포스터 만들기");
    }
    grdMain.redraw();
    if (btnSave) {
        btnSave.click();
        var c3 = await waitDialog(3000);
        var a3 = await waitDialog(4000);
        logs.push({date: "7/24", confirm: c3, alert: a3});
    }
    await new Promise(r => setTimeout(r, 1500));

    // 최종 재조회
    var btnSearch = main.lookup("btnSearch");
    if (btnSearch) {
        btnSearch.click();
    }
    
    return {status: "updated", logs: logs};
}

window.__updateResult = null;
updateAll().then(function(res) {
    window.__updateResult = res;
}).catch(function(err) {
    window.__updateResult = {error: err.toString()};
});

return "Update sequence started...";
"""

try:
    res = driver.execute_script(JS_UPDATE_CONTENTS)
    print("Update process launched:", res)
except Exception as e:
    print("Error:", e)

# 결과 대기 (최대 40초)
update_result = None
for attempt in range(40):
    time.sleep(1.0)
    try:
        val = driver.execute_script("return window.__updateResult;")
        if val is not None:
            update_result = val
            break
    except: pass

print("UPDATE RESULTS:")
print(json.dumps(update_result, ensure_ascii=True, indent=2))

driver.save_screenshot("scratch/screenshot.png")
print("Screenshot saved.")
driver.quit()
