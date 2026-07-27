import io, sys, json
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

JS_DIAGNOSE_POP = """
var pop = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai && ai.app && ai.app.id.indexOf("p11") !== -1;
});
if (!pop) return {error: "Popup app (p11) not found"};

var ctrls = [];
pop.getContainer().getAllRecursiveChildren().forEach(function(c) {
    var textVal = c.value || c.text || "";
    if (c.type === "button" || textVal.indexOf("닫기") !== -1) {
        ctrls.push({
            id: c.id,
            type: c.type,
            value: textVal,
            visible: c.visible
        });
    }
});

return ctrls;
"""

try:
    res = driver.execute_script(JS_DIAGNOSE_POP)
    print("POPUP BUTTON CONTROLS:")
    print(json.dumps(res, ensure_ascii=False, indent=2))
except Exception as e:
    print("Error:", e)

driver.quit()
