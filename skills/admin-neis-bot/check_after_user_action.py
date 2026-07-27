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

JS_CHECK = """
var closedCount = 0;
// 혹시나 여전히 남아있는 예전 대화상자/컨펌창이 있다면 정리하기 위해 X 버튼 클릭 시도
var xButtons = document.querySelectorAll('.cl-dialog-close');
xButtons.forEach(function(btn) {
    try { btn.click(); closedCount++; } catch(e) {}
});

var main = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce01_m07";
});

var pop = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai && ai.app && ai.app.id.indexOf("p11") !== -1;
});

return {
    closedCount: closedCount,
    hasMain: !!main,
    hasPopup: !!pop,
    popupId: pop ? pop.app.id : null
};
"""

try:
    res = driver.execute_script(JS_CHECK)
    print("STATE CHECK:")
    print(json.dumps(res, ensure_ascii=False, indent=2))
except Exception as e:
    print("Error executing JS:", e)

driver.save_screenshot("scratch/screenshot.png")
print("Screenshot saved to scratch/screenshot.png")
driver.quit()
