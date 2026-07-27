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

JS_SAVE_FINAL = """
var pop = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai && ai.app && ai.app.id.indexOf("p11") !== -1;
});
if (!pop) return {error: "Popup app (p11) not found"};

// cpr 컴포넌트 레벨에서 다이얼로그 확인 버튼 클릭하는 헬퍼 함수
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
                                try {
                                    c.click();
                                    clicked = true;
                                } catch(e) {}
                            }
                        }
                    });
                }
            } catch(err) {}
        }
    });
    return clicked;
}

// 다이얼로그 출현 대기 수락 (Promise 기반)
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

async function runRemaining() {
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
        
        // 1. 일자 클릭 선택
        grdActYmd.selectRows([item.idx]);
        await new Promise(r => setTimeout(r, 800)); // 값 로드 대기
        
        // 2. 값 대입 및 redraw
        taCn.value = item.content;
        taCn.redraw();
        neHr.value = item.time;
        neHr.redraw();
        
        // value-change 강제 이벤트
        try {
            taCn.dispatchEvent(new cpr.events.CValueChangeEvent("value-change", {newValue: item.content}));
            neHr.dispatchEvent(new cpr.events.CValueChangeEvent("value-change", {newValue: item.time}));
        } catch(e) {}
        
        // 3. 학생 전체 선택
        grdMain.checkAllRow();
        await new Promise(r => setTimeout(r, 500));
        
        // 4. 저장 클릭
        if (btnSave) {
            btnSave.click();
        }
        
        // 5. "저장하시겠습니까?" 컨펌 다이얼로그 대기 및 승인
        var confirmClicked = await waitAndClickCprDialog(3000);
        
        // 6. "저장되었습니다." 얼럿 다이얼로그 대기 및 승인 (서버 통신 고려 넉넉하게 대기)
        var alertClicked = await waitAndClickCprDialog(4000);
        
        log.push({
            idx: item.idx,
            content: item.content,
            confirmClicked: confirmClicked,
            alertClicked: alertClicked
        });
        
        await new Promise(r => setTimeout(r, 1500));
    }
    
    // 7. 모든 등록이 무사히 완료되면 [닫기] 버튼 클릭으로 일괄등록 창 닫기
    var btnClose = pop.lookup("btnClose");
    if (btnClose) {
        btnClose.click();
    }
    
    return {status: "all_saved", log: log};
}

window.__finalResult = null;
runRemaining().then(function(res) {
    window.__finalResult = res;
}).catch(function(err) {
    window.__finalResult = {error: err.toString()};
});

return "Final saving sequence started...";
"""

try:
    res = driver.execute_script(JS_SAVE_FINAL)
    print("Execution response:", res)
except Exception as e:
    print("Error launching final save:", e)

# 비동기 실행 결과 완료 대기 (최대 20초)
final_result = None
for attempt in range(20):
    time.sleep(1.0)
    try:
        val = driver.execute_script("return window.__finalResult;")
        if val is not None:
            final_result = val
            break
    except: pass

print("FINAL SAVE RESULTS:")
print(json.dumps(final_result, ensure_ascii=False, indent=2))

# 완료 후 스크린샷 캡처
driver.save_screenshot("scratch/screenshot.png")
print("Screenshot saved to scratch/screenshot.png")
driver.quit()
