from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import json

REMOTE_PORT = 9222

def main():
    opts = Options()
    opts.add_experimental_option("debuggerAddress", f"localhost:{REMOTE_PORT}")
    driver = webdriver.Chrome(options=opts)
    
    handles = driver.window_handles
    target_handle = None
    for handle in handles:
        driver.switch_to.window(handle)
        driver.switch_to.default_content()
        if "경상북도교육청" in driver.title or "나이스" in driver.title or "시스템" in driver.title:
            target_handle = handle
            break
            
    if not target_handle:
        print("Could not find NEIS window")
        return
        
    driver.switch_to.window(target_handle)
    driver.switch_to.default_content()
    
    # Print all running app instance IDs
    app_ids = driver.execute_script("""
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        return instances.map(function(ai) {
            return {
                id: ai.app ? ai.app.id : null,
                title: ai.title || ""
            };
        });
    """)
    print("Running App Instances:")
    print(json.dumps(app_ids, indent=2))

if __name__ == "__main__":
    main()
