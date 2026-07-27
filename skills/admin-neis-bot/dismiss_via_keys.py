import io, sys, time, json
import ctypes

# 윈도우 가상 키코드 정의 (Enter: 0x0D)
def press_enter():
    # Enter key down
    ctypes.windll.user32.keybd_event(0x0D, 0, 0, 0)
    time.sleep(0.05)
    # Enter key up
    ctypes.windll.user32.keybd_event(0x0D, 0, 2, 0)
    print("Sent ENTER key event.")

# Alert가 닫힐 때까지 Enter 키 3번 연타
for _ in range(3):
    press_enter()
    time.sleep(0.5)

# 이제 셀레늄 기동
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

# Dump popup status
JS_STATUS = """
var pop = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai && ai.app && ai.app.id.indexOf("p11") !== -1;
});
if (!pop) return {error: "Popup app (p11) not found"};

return {
    appId: pop.app.id,
    isModified: pop.lookup("dsGicRec") ? pop.lookup("dsGicRec").isModified() : null
};
"""

try:
    res = driver.execute_script(JS_STATUS)
    print("POPUP STATUS AFTER DISMISS:")
    print(json.dumps(res, ensure_ascii=False, indent=2))
except Exception as e:
    print("Error:", e)

driver.save_screenshot("scratch/screenshot.png")
print("Screenshot saved to scratch/screenshot.png")
driver.quit()
