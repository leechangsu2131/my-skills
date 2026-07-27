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

JS_DUMP_POP_CONTROLS = """
var main = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce01_m07";
});
if (!main) return {error: "Main app not found"};

// 일괄등록 클릭하여 팝업 띄우기
var btnBatchReg = null;
main.getContainer().getAllRecursiveChildren().forEach(function(c) {
    if (c.type === "button") {
        var val = c.value || c.text || "";
        if (val.indexOf("일괄등록") !== -1 || val.indexOf("일괄") !== -1) {
            btnBatchReg = c;
        }
    }
});

if (btnBatchReg) {
    btnBatchReg.click();
}

async function dumpCtrls() {
    await new Promise(r => setTimeout(r, 2500)); // 팝업 대기
    
    var pop = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
        return ai && ai.app && ai.app.id.indexOf("p11") !== -1;
    });
    if (!pop) return {error: "Popup not found"};
    
    var list = [];
    pop.getContainer().getAllRecursiveChildren().forEach(function(c) {
        list.push({
            id: c.id,
            type: c.type,
            value: c.value || "",
            visible: c.visible
        });
    });
    return list;
}

window.__dumpResult = null;
dumpCtrls().then(function(res) {
    window.__dumpResult = res;
});

return "Dump started...";
"""

try:
    res = driver.execute_script(JS_DUMP_POP_CONTROLS)
    print("Launched dump:", res)
except Exception as e:
    print("Error:", e)

# 결과 대기 (최대 10초)
dump_result = None
for attempt in range(10):
    time.sleep(1.0)
    try:
        val = driver.execute_script("return window.__dumpResult;")
        if val is not None:
            dump_result = val
            break
    except: pass

print("POPUP ALL CONTROLS:")
print(json.dumps(dump_result, ensure_ascii=True, indent=2))

driver.quit()
