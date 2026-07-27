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

JS_REDO_SAFELY = """
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

// 특정 일자의 기존 모든 데이터 삭제 및 저장하는 헬퍼
async function clearRecordsForDate(idx) {
    grdActYmd.selectRows([idx]);
    await new Promise(r => setTimeout(r, 2000));
    
    var count = dsGicRec.getRowCount();
    if (count === 0) return {msg: "Already empty"};
    
    // 전체 체크 해제 후 재체크
    for (var r=0; r<count; r++) {
        grdMain.setCheckRowIndex(r, false);
    }
    for (var r=0; r<count; r++) {
        grdMain.setCheckRowIndex(r, true);
    }
    grdMain.redraw();
    await new Promise(r => setTimeout(r, 500));
    
    var btnDelete = main.lookup("btnDelete");
    if (btnDelete) {
        btnDelete.click();
        await waitDialog(2000);
        await new Promise(r => setTimeout(r, 1000));
        
        var btnSave = main.lookup("btnSave");
        if (btnSave) {
            btnSave.click();
            await waitDialog(3000); // 저장하시겠습니까?
            await waitDialog(4000); // 저장되었습니다.
        }
    }
    return {msg: "Cleared"};
}

async function runRedo() {
    var logs = [];
    
    // STEP 1: 7/9, 7/24 기존 데이터 깨끗하게 지우기
    var c1 = await clearRecordsForDate(0);
    logs.push({action: "clear 7/9", res: c1});
    await new Promise(r => setTimeout(r, 1500));
    
    var c2 = await clearRecordsForDate(2);
    logs.push({action: "clear 7/24", res: c2});
    await new Promise(r => setTimeout(r, 1500));

    // STEP 2: 일괄등록 팝업 열기
    var btnBatchReg = null;
    main.getContainer().getAllRecursiveChildren().forEach(function(c) {
        if (c.type === "button") {
            var val = c.value || c.text || "";
            if (val.indexOf("일괄등록") !== -1 || val.indexOf("일괄") !== -1) {
                btnBatchReg = c;
            }
        }
    });
    if (!btnBatchReg) return {error: "btnBatchReg not found"};
    
    btnBatchReg.click();
    await new Promise(r => setTimeout(r, 2500)); // 팝업 로딩
    
    var pop = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
        return ai && ai.app && ai.app.id.indexOf("p11") !== -1;
    });
    if (!pop) return {error: "Popup app (p11) not found"};
    
    var grdActYmd = pop.lookup("grdActYmd");
    var grdMain = pop.lookup("grdMain");
    var taCn = pop.lookup("gicSpeclActSpablMteCn");
    var neHr = pop.lookup("gicComptHr");
    var cbxServActYn = pop.lookup("cbxServActYn");
    var btnSave = pop.lookup("btnSave");
    
    // 7/9 (Index 0) 와 7/24 (Index 2) 봉사활동 체크박스 클릭하여 자동 완성
    var items = [
        {idx: 0, content: "봉사활동 소양교육"},
        {idx: 2, content: "독서 캠페인 - 독서 활동 홍보 포스터 만들기"}
    ];
    
    for (var k=0; k<items.length; k++) {
        var item = items[k];
        
        // 일자 클릭
        grdActYmd.selectRows([item.idx]);
        await new Promise(r => setTimeout(r, 1000));
        
        // 봉사활동실적입력 체크박스 DOM 또는 dispatchEvent 클릭 트리거
        if (cbxServActYn) {
            cbxServActYn.value = "";
            cbxServActYn.redraw();
            
            var dom = cbxServActYn.getHtmlElement ? cbxServActYn.getHtmlElement() : null;
            if (dom) {
                dom.click(); // 마우스 클릭 트리거
            } else {
                cbxServActYn.value = "Y";
                cbxServActYn.dispatchEvent(new cpr.events.CValueChangeEvent("value-change", {newValue: "Y"}));
            }
            await new Promise(r => setTimeout(r, 1000)); // 시스템 자동완성 바인딩 대기
        }
        
        // 활동내용 기입
        taCn.value = item.content;
        taCn.redraw();
        try {
            taCn.dispatchEvent(new cpr.events.CValueChangeEvent("value-change", {newValue: item.content}));
        } catch(e) {}
        
        // 학생 전체 체크
        grdMain.checkAllRow();
        await new Promise(r => setTimeout(r, 600));
        
        // 저장 클릭
        if (btnSave) {
            btnSave.click();
        }
        
        // 컨펌 및 완료 대기 수락
        var confirmClicked = await waitAndClickCprDialog(3000);
        var alertClicked = await waitAndClickCprDialog(4000);
        
        logs.push({
            action: "save batch " + item.idx,
            confirm: confirmClicked,
            alert: alertClicked
        });
        
        await new Promise(r => setTimeout(r, 1500));
    }
    
    // [닫기] 클릭으로 종료
    var btnCancel = pop.lookup("btnCancel");
    if (btnCancel) {
        btnCancel.click();
    }
    
    // cpr 다이얼로그 자동 확인 함수 (내부 선언)
    function waitAndClickCprDialog(timeoutMs) {
        return new Promise(async (resolve) => {
            var start = Date.now();
            while (Date.now() - start < timeoutMs) {
                if (clickCprDialogOk()) {
                    resolve(true);
                    return;
                }
                await new Promise(r => setTimeout(r, 250));
            }
            resolve(false);
        });
    }
    
    return {status: "completed", logs: logs};
}

window.__redoResult = null;
runRedo().then(function(res) {
    window.__redoResult = res;
}).catch(function(err) {
    window.__redoResult = {error: err.toString()};
});

return "Redo started...";
"""

try:
    res = driver.execute_script(JS_REDO_SAFELY)
    print("Execution response:", res)
except Exception as e:
    print("Error:", e)

# 결과 대기 (최대 45초)
redo_result = None
for attempt in range(45):
    time.sleep(1.0)
    try:
        val = driver.execute_script("return window.__redoResult;")
        if val is not None:
            redo_result = val
            break
    except: pass

print("REDO RESULTS:")
print(json.dumps(redo_result, ensure_ascii=True, indent=2))
driver.quit()
