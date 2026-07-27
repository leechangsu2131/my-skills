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

JS_CLICK_CPR_DIALOG_SAFE = """
var clickedCount = 0;
var logs = [];

var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
apps.forEach(function(ai) {
    if (ai && ai.app && (ai.app.id.indexOf("confirm") !== -1 || ai.app.id.indexOf("alert") !== -1 || ai.app.id.indexOf("cmn") !== -1)) {
        logs.push("Found cmn app: " + ai.app.id);
        try {
            var container = ai.getContainer ? ai.getContainer() : null;
            if (container && container.getAllRecursiveChildren) {
                container.getAllRecursiveChildren().forEach(function(c) {
                    if (c && c.type === "button") {
                        var textVal = c.value || c.text || "";
                        logs.push("Button found: id=" + c.id + ", value=" + textVal);
                        if (textVal === "예" || textVal === "확인" || textVal.indexOf("확인") !== -1 || textVal.indexOf("예") !== -1) {
                            try {
                                c.click();
                                clickedCount++;
                                logs.push("Clicked cpr button: " + c.id);
                            } catch(e) {
                                logs.push("Click error: " + e.toString());
                            }
                        }
                    }
                });
            }
        } catch(err) {
            logs.push("Error container: " + err.toString());
        }
    }
});

return {clickedCount: clickedCount, logs: logs};
"""

try:
    res = driver.execute_script(JS_CLICK_CPR_DIALOG_SAFE)
    print("CPR CLICK RESULT:")
    print(json.dumps(res, ensure_ascii=False, indent=2))
except Exception as e:
    print("Error executing JS:", e)

# 2초 대기하여 저장 완료 얼럿이 뜨는지 캡처
time.sleep(2.0)
driver.save_screenshot("scratch/screenshot.png")
print("Screenshot saved to scratch/screenshot.png")
driver.quit()
