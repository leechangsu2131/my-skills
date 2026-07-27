import io, sys, time, json, os
# Disable internet check for webdriver-manager
os.environ['WDM_LOCAL'] = '1'
os.environ['WDM_SSL_VERIFY'] = '0'
os.environ['WDM_LOG'] = '0'
os.environ['WDM_LOG_LEVEL'] = '0'
os.environ['WDM_LOG_LEVEL_NAME'] = 'CRITICAL'

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

opts = Options()
opts.add_experimental_option("debuggerAddress", "localhost:9222")
driver = webdriver.Chrome(options=opts)

# Find the main e-NEIS window
target_handle = None
for handle in driver.window_handles:
    driver.switch_to.window(handle)
    driver.switch_to.default_content()
    try:
        if driver.execute_script("return typeof cpr !== 'undefined';") and "vpn" not in driver.current_url.lower():
            target_handle = handle
            break
    except: pass

print(f"[connect] {driver.title}")

JS_STEP_1 = """
// 1. 모든 팝업창 닫기 (DOM '닫기' 또는 X 아이콘 요소들 클릭)
var all = document.querySelectorAll('*');
var closedCount = 0;
for (var i = 0; i < all.length; i++) {
    var el = all[i];
    var text = (el.innerText || el.textContent || "").trim();
    if (text === "닫기" && (el.tagName === "SPAN" || el.tagName === "DIV" || el.tagName === "BUTTON")) {
        var target = el;
        for (var d=0; d<5; d++) {
            if (target.classList && (target.classList.contains("cl-button") || target.tagName === "BUTTON")) {
                break;
            }
            if (target.parentElement) target = target.parentElement;
            else break;
        }
        try {
            target.click();
            closedCount++;
        } catch(e) {}
    }
}

var xButtons = document.querySelectorAll('.cl-dialog-close');
xButtons.forEach(function(btn) {
    try {
        btn.click();
        closedCount++;
    } catch(e) {}
});

// 2. 메인 화면 조회 트리거
var main = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce01_m07";
});
if (!main) return {error: "Main app not found", closedCount: closedCount};

var btnSearch = main.lookup("btnSearch");
if (btnSearch) {
    btnSearch.click();
    return {ok: true, closedCount: closedCount, step: "query_triggered"};
}
return {error: "btnSearch not found on main", closedCount: closedCount};
"""

print("[run] 1단계: 팝업 닫기 및 메인 조회 클릭...")
res_1 = driver.execute_script(JS_STEP_1)
print("  결과:", res_1)

# 메인 조회 로딩 대기 (6초)
print("메인 조회 로딩 대기 6초...")
time.sleep(6.0)

JS_STEP_2 = """
var main = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce01_m07";
});
if (!main) return {error: "Main app not found in Step 2"};

var btnBnde = main.lookup("btnBndeSave"); // 일괄등록 버튼
if (btnBnde) {
    btnBnde.click();
    return {ok: true};
}
return {error: "btnBndeSave not found on main"};
"""

print("[run] 2단계: 일괄등록 버튼 클릭...")
res_2 = driver.execute_script(JS_STEP_2)
print("  결과:", res_2)

# 일괄등록 팝업창 로딩 및 데이터 바인딩 대기 (6초)
print("일괄등록 팝업 로딩 및 데이터 바인딩 대기 6초...")
time.sleep(6.0)

JS_STEP_3_DUMP = """
var pop = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai && ai.app && ai.app.id.indexOf("p11") !== -1;
});
if (!pop) return {error: "Batch popup app not found after reopening"};

var datasets = [];
var dc = pop.getAllDataControls ? pop.getAllDataControls() : [];
dc.forEach(function(ds) {
    var cols = [];
    try { cols = ds.getColumnNames(); } catch(e) {}
    var rows = [];
    // DataMap은 getRowCount가 없으므로 체크
    if (ds.getRowCount) {
        try {
            var rCount = ds.getRowCount();
            var limit = Math.min(rCount, 20);
            for (var r=0; r<limit; r++) {
                var row = {};
                cols.forEach(function(col) {
                    row[col] = ds.getValue(r, col);
                });
                rows.push(row);
            }
            datasets.push({id: ds.id, type: ds.type, rowCount: rCount, data: rows});
        } catch(dsErr) {
            datasets.push({id: ds.id, type: ds.type, error: dsErr.toString()});
        }
    } else {
        datasets.push({id: ds.id, type: ds.type, isMap: true});
    }
});

// 팝업 내부의 컨트롤 목록들 추출
var controls = [];
if (pop.getChildren) {
    pop.getChildren().forEach(function(ctrl) {
        controls.push({id: ctrl.id, type: ctrl.type, visible: ctrl.visible});
    });
}

return {
    appId: pop.app.id,
    datasets: datasets,
    controls: controls
};
"""

print("[run] 3단계: 일괄등록 팝업 데이터 덤프...")
try:
    res_3 = driver.execute_script(JS_STEP_3_DUMP)
    print("덤프 결과:")
    print(json.dumps(res_3, ensure_ascii=False, indent=2))
except Exception as e:
    print("3단계 덤프 중 파이썬 예외:", e)

driver.save_screenshot("scratch/screenshot.png")
print("스크린샷 저장 완료.")
driver.quit()
