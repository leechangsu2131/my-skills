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

JS_FIND_DOM = """
var textareas = [];
document.querySelectorAll('textarea').forEach(function(el) {
    textareas.push({
        id: el.id,
        className: el.className,
        value: el.value,
        placeholder: el.placeholder,
        visible: el.offsetWidth > 0
    });
});

var inputs = [];
document.querySelectorAll('input').forEach(function(el) {
    if (el.offsetWidth > 0) {
        inputs.push({
            id: el.id,
            className: el.className,
            type: el.type,
            value: el.value
        });
    }
});

return {
    textareas: textareas,
    inputs: inputs
};
"""

try:
    res = driver.execute_script(JS_FIND_DOM)
    print("DOM ELEMENTS:")
    print(json.dumps(res, ensure_ascii=False, indent=2))
except Exception as e:
    print("Error:", e)

driver.quit()
