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

# Handle current alert to print exactly what it says
alert_text = "No alert"
try:
    alert = driver.switch_to.alert
    alert_text = alert.text
    print(f"RAW Alert text: {alert_text}")
    # UTF-8 복원을 시도하거나 바이트를 파악하기 위해 byte형태로 인코딩해 출력
    try:
        raw_bytes = alert_text.encode('utf-8', errors='replace')
        print(f"Alert Bytes (UTF-8): {raw_bytes}")
        raw_bytes_cp949 = alert_text.encode('cp949', errors='replace')
        print(f"Alert Bytes (CP949): {raw_bytes_cp949}")
    except: pass
    alert.accept()
    print("Alert closed.")
except Exception as e:
    print("Error checking alert:", e)

# Dump all inputs on main screen
JS_DUMP_INPUTS = """
var inputs = [];
document.querySelectorAll('input').forEach(function(el) {
    if (el.offsetWidth > 0 || el.offsetHeight > 0) {
        // eXbuilder6 컴포넌트 uuid나 id 탐색
        var cprControl = null;
        try {
            // eXbuilder 엘리먼트에서 컨트롤 객체 얻기
            var app = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
                return ai.getContainer().getAllRecursiveChildren().some(function(c) {
                    return c.getActualRect && c.id === el.id;
                });
            });
            if (app) {
                var ctrl = app.lookup(el.id);
                if (ctrl) {
                    cprControl = {
                        id: ctrl.id,
                        type: ctrl.type,
                        value: ctrl.value,
                        fieldLabel: ctrl.fieldLabel || ""
                    };
                }
            }
        } catch(e) {}

        inputs.push({
            id: el.id,
            className: el.className,
            type: el.type,
            value: el.value,
            placeholder: el.placeholder,
            cprControl: cprControl
        });
    }
});
return inputs;
"""

try:
    res = driver.execute_script(JS_DUMP_INPUTS)
    print("ALL VISIBLE INPUTS:")
    print(json.dumps(res, ensure_ascii=False, indent=2))
except Exception as e:
    print("Error dumping inputs:", e)

driver.save_screenshot("scratch/screenshot.png")
driver.quit()
