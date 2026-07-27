import io, sys, time, json
import ctypes

def focus_and_enter():
    EnumWindows = ctypes.windll.user32.EnumWindows
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
    GetWindowText = ctypes.windll.user32.GetWindowTextW
    GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
    
    target_hwnd = []
    def foreach_window(hwnd, lParam):
        length = GetWindowTextLength(hwnd)
        buff = ctypes.create_unicode_buffer(length + 1)
        GetWindowText(hwnd, buff, length + 1)
        title = buff.value
        # 나이스 창 제목 후보 필터링
        if "경상북도" in title or "나이스" in title:
            target_hwnd.append((hwnd, title))
        return True
        
    EnumWindows(EnumWindowsProc(foreach_window), 0)
    
    if target_hwnd:
        # 가장 적절한 것 선택
        hwnd, title = target_hwnd[0]
        print(f"Found active NEIS window: '{title}' (hwnd: {hwnd})")
        # 포커스 활성화
        ctypes.windll.user32.ShowWindow(hwnd, 9) # Restore
        ctypes.windll.user32.SetForegroundWindow(hwnd)
        time.sleep(0.5)
        # Enter 입력 (3회 루프)
        for _ in range(3):
            ctypes.windll.user32.keybd_event(0x0D, 0, 0, 0)
            time.sleep(0.05)
            ctypes.windll.user32.keybd_event(0x0D, 0, 2, 0)
            print("Sent Enter key event to window.")
            time.sleep(0.5)
    else:
        print("NEIS window not found by title. Sending Enter to active foreground...")
        # fallback: 그냥 현재 활성화된 아무 창에나 엔터를 날려봄
        for _ in range(3):
            ctypes.windll.user32.keybd_event(0x0D, 0, 0, 0)
            time.sleep(0.05)
            ctypes.windll.user32.keybd_event(0x0D, 0, 2, 0)
            time.sleep(0.5)

print("Starting window focus and dismiss...")
focus_and_enter()
print("Focus and key events completed. Initiating selenium...")

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

driver_path = r"C:\Users\lee21\.cache\selenium\chromedriver\win64\150.0.7871.115\chromedriver.exe"
service = Service(executable_path=driver_path)

opts = Options()
opts.add_experimental_option("debuggerAddress", "localhost:9222")
driver = webdriver.Chrome(service=service, options=opts)

# Find target handle
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

# Dump status
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
    print("POPUP STATUS AFTER RECOVERY:")
    print(json.dumps(res, ensure_ascii=False, indent=2))
except Exception as e:
    print("Error getting status:", e)

driver.save_screenshot("scratch/screenshot.png")
print("Screenshot saved to scratch/screenshot.png")
driver.quit()
