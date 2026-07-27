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

# cpr 컴포넌트 레벨에서 다이얼로그 확인 버튼 클릭하는 헬퍼 함수
JS_FULL_FIX = """
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

// ============================================================
// STEP 1: 7/24 중복 2세트 삭제
// dsGicRec에 54행 (18명 * 3세트), 2~3번째 세트(36개) 삭제 필요
// ============================================================
async function step1_delete724() {
    // 7/24 날짜 선택 (인덱스 2)
    grdActYmd.selectRows([2]);
    await new Promise(r => setTimeout(r, 2000));
    
    var count = dsGicRec.getRowCount();
    console.log("7/24 total rows:", count);
    
    // speclActComptSeq로 그룹핑하여 중복 파악
    var seqMap = {};
    for (var r=0; r<count; r++) {
        var seq = dsGicRec.getValue(r, "speclActComptSeq");
        var stuNo = dsGicRec.getValue(r, "stuInvlNo");
        if (!seqMap[seq]) seqMap[seq] = [];
        seqMap[seq].push({row: r, stuNo: stuNo});
    }
    
    var seqs = Object.keys(seqMap).sort();
    console.log("Distinct seq groups:", JSON.stringify(seqs));
    
    // 첫 번째 세트를 제외한 2, 3번째 세트의 학생 행 선택하여 삭제
    var seqsToDelete = seqs.slice(1); // 두번째, 세번째 세트
    var log = {seqs: seqs, seqsToDelete: seqsToDelete, rowsDeleted: []};
    
    // 삭제할 행 번호 수집
    var rowsToDelete = [];
    seqsToDelete.forEach(function(seq) {
        seqMap[seq].forEach(function(item) {
            rowsToDelete.push(item.row);
        });
    });
    
    // 행 역순으로 삭제 (인덱스 안정성)
    rowsToDelete.sort(function(a,b) { return b-a; });
    rowsToDelete.forEach(function(r) {
        // dsGicRec 행 체크 후 삭제 제출
        grdMain.selectRows([r]);
    });
    
    // 삭제 버튼 lookup
    var btnDelete = main.lookup("btnDelete");
    
    if (!btnDelete) {
        log.error = "btnDelete not found";
        return log;
    }
    
    // 삭제 대상 행들 체크 (2번째, 3번째 세트)
    // 먼저 체크 해제
    grdMain.uncheckAllRow();
    
    // 2, 3번째 세트 행 체크
    rowsToDelete.forEach(function(r) {
        grdMain.checkRow(r);
    });
    
    btnDelete.click();
    var confirmClicked = await waitDialog(3000);
    var alertClicked = await waitDialog(4000);
    
    log.rowsDeleted = rowsToDelete.length;
    log.confirmClicked = confirmClicked;
    log.alertClicked = alertClicked;
    
    return log;
}

// ============================================================
// STEP 2: 7/9 봉사활동 소양교육 등록 (일괄등록 팝업 사용)
// ============================================================
async function step2_add709() {
    // 7/9 날짜 선택 (인덱스 0)
    grdActYmd.selectRows([0]);
    await new Promise(r => setTimeout(r, 2000));
    
    // 일괄등록 버튼 찾기
    var btnBatch = main.lookup("btnBatchReg");
    if (!btnBatch) {
        // 대안: 일괄등록이라는 텍스트의 버튼 찾기
        var allCtrls = main.getContainer ? main.getContainer().getAllRecursiveChildren() : [];
        allCtrls.forEach(function(c) {
            if (c.type === "button") {
                var val = c.value || c.text || "";
                if (val.indexOf("일괄") !== -1) {
                    btnBatch = c;
                }
            }
        });
    }
    
    if (!btnBatch) return {error: "일괄등록 버튼을 찾지 못함"};
    btnBatch.click();
    await new Promise(r => setTimeout(r, 2000));
    
    return {success: true, msg: "일괄등록 팝업 오픈 시도"};
}

// 전체 실행
window.__fixResult = null;
async function runFix() {
    var r1 = await step1_delete724();
    await new Promise(r => setTimeout(r, 2000));
    
    // 삭제 후 7/24 다시 조회
    grdActYmd.selectRows([2]);
    await new Promise(r => setTimeout(r, 2000));
    var remainCount = dsGicRec.getRowCount();
    
    return {
        step1_delete724: r1,
        after724Count: remainCount
    };
}

runFix().then(function(res) {
    window.__fixResult = res;
}).catch(function(err) {
    window.__fixResult = {error: err.toString()};
});
return "Fix started...";
"""

try:
    res = driver.execute_script(JS_FULL_FIX)
    print("Started:", res)
except Exception as e:
    print("Error:", e)

# 비동기 완료 대기 (최대 30초)
fix_result = None
for attempt in range(30):
    time.sleep(1.0)
    try:
        val = driver.execute_script("return window.__fixResult;")
        if val is not None:
            fix_result = val
            break
    except: pass

print("FIX RESULT:")
print(json.dumps(fix_result, ensure_ascii=False, indent=2))

driver.save_screenshot("scratch/screenshot.png")
print("Screenshot saved.")
driver.quit()
