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

JS_BATCH_ADD_SAFE = """
var main = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce01_m07";
});
if (!main) return {error: "Main app not found"};

// 1. 조회 버튼 먼저 클릭하여 메인 화면 로드
var btnSearch = main.lookup("btnSearch");
if (btnSearch) {
    btnSearch.click();
}

async function runBatchAdd() {
    // 3.5초 대기 (조회 완료 및 컨트롤 활성화)
    await new Promise(r => setTimeout(r, 3500));
    
    // 2. 일괄등록 버튼 텍스트 매칭으로 안전하게 찾기
    var btnBatchReg = null;
    main.getContainer().getAllRecursiveChildren().forEach(function(c) {
        if (c.type === "button") {
            var val = c.value || c.text || "";
            if (val.indexOf("일괄등록") !== -1 || val.indexOf("일괄") !== -1) {
                btnBatchReg = c;
            }
        }
    });
    
    if (!btnBatchReg) return {error: "일괄등록 버튼을 찾지 못했습니다."};
    
    // 3. 일괄등록 클릭
    btnBatchReg.click();
    await new Promise(r => setTimeout(r, 2500)); // 팝업창 로딩 대기
    
    var pop = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
        return ai && ai.app && ai.app.id.indexOf("p11") !== -1;
    });
    if (!pop) return {error: "일괄등록 팝업창(p11)을 찾지 못했습니다."};
    
    // cpr 다이얼로그 자동 확인 함수
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

    async function waitAndClickCprDialog(timeoutMs) {
        var start = Date.now();
        while (Date.now() - start < timeoutMs) {
            if (clickCprDialogOk()) {
                return true;
            }
            await new Promise(r => setTimeout(r, 250));
        }
        return false;
    }

    var grdActYmd = pop.lookup("grdActYmd");
    var grdMain = pop.lookup("grdMain");
    var taCn = pop.lookup("gicSpeclActSpablMteCn");
    var neHr = pop.lookup("gicComptHr");
    var btnSave = pop.lookup("btnSave");
    
    var batchLogs = [];
    
    // 7/9 (Index 0), 7/16 (Index 1) 등록
    var items = [
        {idx: 0, time: 1, content: "봉사활동 소양교육"},
        {idx: 1, time: 2, content: "도서관에서 지켜야 할 예절 토의하기, 원하는 책 친구에게 소개하기"}
    ];
    
    for (var k=0; k<items.length; k++) {
        var item = items[k];
        
        // 일자 클릭
        grdActYmd.selectRows([item.idx]);
        await new Promise(r => setTimeout(r, 1000));
        
        // 값 입력
        taCn.value = item.content;
        taCn.redraw();
        neHr.value = item.time;
        neHr.redraw();
        
        try {
            taCn.dispatchEvent(new cpr.events.CValueChangeEvent("value-change", {newValue: item.content}));
            neHr.dispatchEvent(new cpr.events.CValueChangeEvent("value-change", {newValue: item.time}));
        } catch(e) {}
        
        // 학생 전체 체크
        grdMain.checkAllRow();
        await new Promise(r => setTimeout(r, 600));
        
        // 저장 클릭
        if (btnSave) {
            btnSave.click();
        }
        
        // "저장하시겠습니까?" 컨펌
        var confirmClicked = await waitAndClickCprDialog(3000);
        // "저장되었습니다." 얼럿
        var alertClicked = await waitAndClickCprDialog(4000);
        
        batchLogs.push({
            idx: item.idx,
            content: item.content,
            confirmClicked: confirmClicked,
            alertClicked: alertClicked
        });
        
        await new Promise(r => setTimeout(r, 1800));
    }
    
    // [닫기] (btnCancel) 클릭으로 일괄등록 창 종료
    var btnCancel = pop.lookup("btnCancel");
    if (btnCancel) {
        btnCancel.click();
    }
    
    return {status: "done", logs: batchLogs};
}

window.__batchResult = null;
runBatchAdd().then(function(res) {
    window.__batchResult = res;
}).catch(function(err) {
    window.__batchResult = {error: err.toString()};
});

return "Safe batch registration started...";
"""

try:
    res = driver.execute_script(JS_BATCH_ADD_SAFE)
    print("Execution response:", res)
except Exception as e:
    print("Error:", e)

# 결과 대기 (최대 30초)
batch_result = None
for attempt in range(30):
    time.sleep(1.0)
    try:
        val = driver.execute_script("return window.__batchResult;")
        if val is not None:
            batch_result = val
            break
    except: pass

print("BATCH ADD RESULTS:")
print(json.dumps(batch_result, ensure_ascii=True, indent=2))

# 팝업이 닫힌 상태에서 새로 조회를 눌러 확인
time.sleep(2.0)
JS_REFRESH = """
var main = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce01_m07";
});
if (main) {
    var btnSearch = main.lookup("btnSearch");
    if (btnSearch) {
        btnSearch.click();
        return "Main search clicked";
    }
}
return "Main app not found";
"""

try:
    res2 = driver.execute_script(JS_REFRESH)
    print("Final search result:", res2)
except Exception as e:
    print("Error:", e)

time.sleep(6.0)
driver.save_screenshot("scratch/screenshot.png")
print("Screenshot saved.")
driver.quit()
