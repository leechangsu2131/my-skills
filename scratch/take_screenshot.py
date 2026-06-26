import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

REMOTE_PORT = 9222

JS_FIND_APP = """
    var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var inst = instances.find(ai => ai.app && ai.app.id.includes("scres20_m00"));
    if (!inst) return {error: "App instance scres20_m00 not found"};
"""

def main():
    opts = Options()
    opts.add_experimental_option("debuggerAddress", f"localhost:{REMOTE_PORT}")
    driver = webdriver.Chrome(options=opts)
    
    target_handle = None
    
    handles = driver.window_handles
    for handle in handles:
        driver.switch_to.window(handle)
        driver.switch_to.default_content()
        try:
            has_cpr = driver.execute_script("return typeof cpr !== 'undefined';")
            if has_cpr:
                app_info = driver.execute_script(JS_FIND_APP + "return {ok: true, appId: inst.app.id};")
                if "ok" in app_info:
                    target_handle = handle
                    break
        except Exception:
            pass
            
    if not target_handle:
        print("Could not find NEIS app window")
        return
        
    driver.switch_to.window(target_handle)
    driver.maximize_window()
    time.sleep(1)
    
    screenshot_path = "scratch/current_screen.png"
    driver.save_screenshot(screenshot_path)
    print(f"Screenshot saved to {screenshot_path}")

if __name__ == "__main__":
    main()
