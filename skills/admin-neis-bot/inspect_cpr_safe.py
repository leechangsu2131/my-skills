import io, sys, time, json, traceback
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoAlertPresentException, TimeoutException

print("Starting safe inspection...")
opts = Options()
opts.add_experimental_option("debuggerAddress", "localhost:9222")
driver = None
try:
    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(5)
    driver.set_script_timeout(5)

    target_handle = None
    print(f"Window handles: {driver.window_handles}")
    for handle in driver.window_handles:
        print(f"Switching to window: {handle}")
        try:
            driver.switch_to.window(handle)
            # Check for alert first
            try:
                alert = driver.switch_to.alert
                print(f"Alert detected: '{alert.text}'. Dismissing it.")
                alert.accept()
                time.sleep(0.5)
            except NoAlertPresentException:
                pass
            
            driver.switch_to.default_content()
            is_cpr = driver.execute_script("return typeof cpr !== 'undefined';")
            url = driver.current_url.lower()
            print(f"  URL: {url}, is_cpr: {is_cpr}")
            if is_cpr and "vpn" not in url:
                target_handle = handle
                print(f"Found target handle: {handle}")
                break
        except Exception as win_err:
            print(f"Error handling window {handle}: {win_err}")

    if not target_handle:
        print("Error: Could not find e-NEIS window with 'cpr' defined safely.")
        sys.exit(1)

    print(f"[connected] {driver.title}")

    JS_INSPECT = """
    var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var result = [];
    apps.forEach(function(ai) {
        var controls = [];
        if (ai.getChildren) {
            ai.getChildren().forEach(function(ctrl) {
                controls.push({id: ctrl.id, type: ctrl.type, visible: ctrl.visible});
            });
        }
        
        var dataControls = [];
        if (ai.getAllDataControls) {
            ai.getAllDataControls().forEach(function(ds) {
                var info = {id: ds.id, type: ds.type};
                if (ds.getRowCount) {
                    try { info.rowCount = ds.getRowCount(); } catch(e) {}
                }
                dataControls.push(info);
            });
        }
        
        result.push({
            appId: ai.app ? ai.app.id : null,
            title: ai.title,
            dataControls: dataControls,
            controls: controls
        });
    });

    return result;
    """

    res = driver.execute_script(JS_INSPECT)
    with open("scratch/inspect_result.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print("Inspection successfully saved to scratch/inspect_result.json")
    
    driver.save_screenshot("scratch/screenshot.png")
    print("Screenshot saved to scratch/screenshot.png")

except Exception as e:
    print("Exception occurred:")
    traceback.print_exc()
finally:
    if driver:
        try:
            driver.quit()
            print("Driver quitted.")
        except: pass
