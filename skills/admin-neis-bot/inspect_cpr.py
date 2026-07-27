import io, sys, time, json, traceback
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

print("Starting inspection...")
opts = Options()
opts.add_experimental_option("debuggerAddress", "localhost:9222")
driver = None
try:
    driver = webdriver.Chrome(options=opts)

    # Find the main e-NEIS window
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
        print("Error: Could not find e-NEIS window with 'cpr' defined.")
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
        
        // Data controls
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

except Exception as e:
    print("Exception occurred:")
    traceback.print_exc()
finally:
    if driver:
        try:
            driver.quit()
            print("Driver quitted.")
        except: pass
