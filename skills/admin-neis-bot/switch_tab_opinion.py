import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

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
    
    print(f"Active window: {driver.title}")
    
    # 1. Dismiss any existing system alerts
    from selenium.common.exceptions import NoAlertPresentException
    try:
        alert = driver.switch_to.alert
        alert.dismiss()
        print("Dismissed browser system alert")
    except NoAlertPresentException:
        pass
        
    # 2. Dismiss ALL active eXBuilder confirm/alert dialogs in parallel
    driver.execute_script("""
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var confirmApps = instances.filter(ai => ai && ai.app && (ai.app.id === "app/cmn/confirm" || ai.app.id === "app/cmn/alert"));
        console.log("Found confirm/alert apps count: " + confirmApps.length);
        
        confirmApps.forEach(function(confirmApp) {
            try {
                var container = confirmApp.getContainer();
                if (container) {
                    var clicked = false;
                    function findAndClick(ctrl) {
                        if (!ctrl) return;
                        var val = ctrl.value || ctrl.text || "";
                        var id = ctrl.id || "";
                        // Try to click Cancel/취소 or OK/확인 to clear
                        if (id === "btnCancel" || val === "취소" || val === "확인" || id === "btnOk" || id === "btnConfirm") {
                            if (typeof ctrl.click === 'function') {
                                try {
                                    ctrl.click();
                                    clicked = true;
                                } catch(e) {}
                            }
                        }
                        if (typeof ctrl.getChildren === 'function') {
                            var children = ctrl.getChildren();
                            for (var j = 0; j < children.length; j++) {
                                findAndClick(children[j]);
                            }
                        }
                    }
                    findAndClick(container);
                }
            } catch(err) {
                console.log("Stale confirm app container skip: " + err);
            }
        });
    """)
    time.sleep(2)
    
    # 3. Find and click the tab item containing "학기말종합의견"
    elements = driver.find_elements(By.XPATH, "//*[contains(text(), '학기말종합의견')]")
    print(f"Found {len(elements)} elements containing '학기말종합의견'")
    
    clicked = False
    for idx, el in enumerate(elements):
        try:
            if el.is_displayed():
                print(f"Clicking visible element [{idx}] (Tag: {el.tag_name}, Class: {el.get_attribute('class')})")
                driver.execute_script("arguments[0].click();", el)
                print("Clicked successfully!")
                clicked = True
                break
        except Exception as e:
            print(f"Failed to click [{idx}]: {e}")
            
    if clicked:
        time.sleep(3)
        screenshot_path = "scratch/current_screen.png"
        driver.save_screenshot(screenshot_path)
        print(f"Screenshot saved to {screenshot_path}")
    else:
        print("No visible tab element found to click")

if __name__ == "__main__":
    main()
