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

print(f"Connected to window: {driver.title}")

# 데이터셋 입력 및 저장 시퀀스 JS
JS_SAVE_ACTIVITIES = """
var pop = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai && ai.app && ai.app.id.indexOf("p11") !== -1;
});
if (!pop) return {error: "Popup app (p11) not found"};

// 저장 완료나 확인 창 닫는 헬퍼 함수
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

// 비동기 방식으로 순차 등록 실행
async function runSequential() {
    var data = [
        {idx: 0, time: 1, content: "봉사활동 소양교육"},
        {idx: 1, time: 2, content: "도서관에서 지켜야 할 예절 토의하기, 원하는 책 친구에게 소개하기"},
        {idx: 2, time: 3, content: "책 광고 - 우리 활동 홍보지 만들기"} // index 2는 2026-07-24 (1시간)
    ];
    // 날짜 매핑: 0: 7/9(1시간), 1: 7/16(2시간), 2: 7/24(1시간)
    // 데이터 2번의 이수시간은 7/24 일자에 1시간이 배정되어 있을 것임.
    
    var grdActYmd = pop.lookup("grdActYmd");
    var grdMain = pop.lookup("grdMain");
    var taCn = pop.lookup("gicSpeclActSpablMteCn");
    var neHr = pop.lookup("gicComptHr");
    var btnSave = pop.lookup("btnSave");
    
    var log = [];
    
    for (var k=0; k<data.length; k++) {
        var item = data[k];
        
        // 1. 일자 선택
        grdActYmd.selectRows([item.idx]);
        await new Promise(r => setTimeout(r, 500));
        
        // 2. 값 기입 및 redraw
        taCn.value = item.content;
        taCn.redraw();
        
        // 7/24(idx: 2)는 1시간짜리임. item.time 수정 반영
        var targetHr = item.time;
        if (item.idx === 2) targetHr = 1; 
        neHr.value = targetHr;
        neHr.redraw();
        
        // value-change 이벤트 트리거
        try {
            taCn.dispatchEvent(new cpr.events.CValueChangeEvent("value-change", {newValue: item.content}));
            neHr.dispatchEvent(new cpr.events.CValueChangeEvent("value-change", {newValue: targetHr}));
        } catch(e) {}
        
        // 3. 학생 전체 체크
        grdMain.checkAllRow();
        await new Promise(r => setTimeout(r, 300));
        
        // 4. 저장 클릭
        if (btnSave) {
            btnSave.click();
        }
        
        // 5. 대기 후 "저장하시겠습니까?" 다이얼로그 수락
        await new Promise(r => setTimeout(r, 800));
        var ok1 = clickDialogOk();
        
        // 6. 대기 후 "저장되었습니다." 다이얼로그 수락
        await new Promise(r => setTimeout(r, 1200));
        var ok2 = clickDialogOk();
        
        log.push({
            idx: item.idx,
            content: item.content,
            dialog1_clicked: ok1,
            dialog2_clicked: ok2
        });
        
        await new Promise(r => setTimeout(r, 1000));
    }
    
    return {status: "done", log: log};
}

// 비동기 함수 실행 후 상위 레벨로 결과 전달을 위해 전역 변수에 바인딩
window.__saveResult = null;
runSequential().then(function(res) {
    window.__saveResult = res;
}).catch(function(err) {
    window.__saveResult = {error: err.toString()};
});

return "Async save sequence started...";
"""

try:
    res = driver.execute_script(JS_SAVE_ACTIVITIES)
    print("Execution response:", res)
except Exception as e:
    print("Error launching JS save sequence:", e)

# 비동기 실행 완료될 때까지 폴링 대기 (최대 20초)
save_result = None
for attempt in range(20):
    time.sleep(1.0)
    try:
        val = driver.execute_script("return window.__saveResult;")
        if val is not None:
            save_result = val
            break
    except: pass

print("SAVE RESULTS:")
print(json.dumps(save_result, ensure_ascii=False, indent=2))

# 결과 화면 확인을 위한 스크린샷 저장
driver.save_screenshot("scratch/screenshot.png")
print("Screenshot saved to scratch/screenshot.png")
driver.quit()
