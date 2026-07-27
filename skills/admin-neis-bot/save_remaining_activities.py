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

# 남은 2개 일자 기입 및 저장 JS 스크립트
JS_SAVE_REMAINING = """
var pop = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai && ai.app && ai.app.id.indexOf("p11") !== -1;
});
if (!pop) return {error: "Popup app (p11) not found"};

// cl-dialog 수락 함수
function clickDialogOk() {
    var dialog = document.querySelector('.cl-dialog');
    if (dialog) {
        var buttons = dialog.querySelectorAll('.cl-button');
        for (var i=0; i<buttons.length; i++) {
            var btn = buttons[i];
            if (btn.textContent.indexOf("확인") !== -1 || btn.textContent.indexOf("예") !== -1 || btn.textContent.indexOf("OK") !== -1) {
                btn.click();
                return true;
            }
        }
    }
    return false;
}

// 특정 cl-dialog가 뜰 때까지 대기하고 수락하는 함수 (Promise 기반)
async function waitAndAcceptDialog(timeoutMs) {
    var start = Date.now();
    while (Date.now() - start < timeoutMs) {
        if (clickDialogOk()) {
            return true;
        }
        await new Promise(r => setTimeout(r, 200));
    }
    return false;
}

async function runRemaining() {
    // 0. 현재 떠 있는 "저장되었습니다." 팝업 확인 클릭
    clickDialogOk();
    await new Promise(r => setTimeout(r, 1000));

    var data = [
        {idx: 1, time: 2, content: "도서관에서 지켜야 할 예절 토의하기, 원하는 책 친구에게 소개하기"},
        {idx: 2, time: 1, content: "책 광고 - 우리 활동 홍보지 만들기"}
    ];

    var grdActYmd = pop.lookup("grdActYmd");
    var grdMain = pop.lookup("grdMain");
    var taCn = pop.lookup("gicSpeclActSpablMteCn");
    var neHr = pop.lookup("gicComptHr");
    var btnSave = pop.lookup("btnSave");
    
    var log = [];
    
    for (var k=0; k<data.length; k++) {
        var item = data[k];
        
        // 1. 일자 클릭
        grdActYmd.selectRows([item.idx]);
        await new Promise(r => setTimeout(r, 800)); // 로딩 대기
        
        // 2. 값 대입 및 redraw
        taCn.value = item.content;
        taCn.redraw();
        neHr.value = item.time;
        neHr.redraw();
        
        // value-change 강제 트리거
        try {
            taCn.dispatchEvent(new cpr.events.CValueChangeEvent("value-change", {newValue: item.content}));
            neHr.dispatchEvent(new cpr.events.CValueChangeEvent("value-change", {newValue: item.time}));
        } catch(e) {}
        
        // 3. 학생 전체 체크
        grdMain.checkAllRow();
        await new Promise(r => setTimeout(r, 400));
        
        // 4. 저장 클릭
        if (btnSave) {
            btnSave.click();
        }
        
        // 5. "저장하시겠습니까?" 컨펌창 대기 및 클릭
        var confirmClicked = await waitAndAcceptDialog(2000);
        
        // 6. "저장되었습니다." 완료창 대기 및 클릭
        var alertClicked = await waitAndAcceptDialog(3000);
        
        log.push({
            idx: item.idx,
            content: item.content,
            confirmClicked: confirmClicked,
            alertClicked: alertClicked
        });
        
        await new Promise(r => setTimeout(r, 1500));
    }
    
    // 7. 모든 저장이 끝나면 팝업 닫기 버튼 클릭
    var btnClose = pop.lookup("btnClose");
    if (btnClose) {
        btnClose.click();
    }
    
    return {status: "completed", log: log};
}

window.__remainingResult = null;
runRemaining().then(function(res) {
    window.__remainingResult = res;
}).catch(function(err) {
    window.__remainingResult = {error: err.toString()};
});

return "Async remaining save started...";
"""

try:
    res = driver.execute_script(JS_SAVE_REMAINING)
    print("Execution response:", res)
except Exception as e:
    print("Error launching remaining save sequence:", e)

# 폴링 대기 (최대 20초)
remaining_result = None
for attempt in range(20):
    time.sleep(1.0)
    try:
        val = driver.execute_script("return window.__remainingResult;")
        if val is not None:
            remaining_result = val
            break
    except: pass

print("REMAINING SAVE RESULTS:")
print(json.dumps(remaining_result, ensure_ascii=False, indent=2))

# 팝업이 닫힌 뒤 메인 화면 상태 캡처
driver.save_screenshot("scratch/screenshot.png")
print("Screenshot saved to scratch/screenshot.png")
driver.quit()
