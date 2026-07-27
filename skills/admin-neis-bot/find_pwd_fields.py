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

# Handle alert first if present
alert_text = None
try:
    alert = driver.switch_to.alert
    alert_text = alert.text
    print(f"Alert detected: {alert_text}")
    alert.accept() # 닫아줌
    print("Alert accepted.")
except Exception as e:
    print("No alert detected or error handling alert:", e)

# Dump control names and look for password fields
JS_FIND_FIELDS = """
var res = {mainCtrls: [], popCtrls: []};

var main = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce01_m07";
});
if (main) {
    main.getContainer().getAllRecursiveChildren().forEach(function(c) {
        var lowerId = (c.id || "").toLowerCase();
        if (lowerId.indexOf("pwd") !== -1 || lowerId.indexOf("pass") !== -1 || lowerId.indexOf("secret") !== -1 || (c.fieldLabel && c.fieldLabel.indexOf("비밀번호") !== -1)) {
            res.mainCtrls.push({id: c.id, type: c.type, fieldLabel: c.fieldLabel || "", value: c.value});
        }
    });
}

var pop = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai && ai.app && ai.app.id.indexOf("p11") !== -1;
});
if (pop) {
    pop.getContainer().getAllRecursiveChildren().forEach(function(c) {
        var lowerId = (c.id || "").toLowerCase();
        if (lowerId.indexOf("pwd") !== -1 || lowerId.indexOf("pass") !== -1 || lowerId.indexOf("secret") !== -1 || (c.fieldLabel && c.fieldLabel.indexOf("비밀번호") !== -1)) {
            res.popCtrls.push({id: c.id, type: c.type, fieldLabel: c.fieldLabel || "", value: c.value});
        }
    });
}

return res;
"""

try:
    res = driver.execute_script(JS_FIND_FIELDS)
    print("PWD FIELDS FOUND:")
    print(json.dumps(res, ensure_ascii=False, indent=2))
except Exception as e:
    print("Error seeking pwd fields:", e)

driver.quit()
