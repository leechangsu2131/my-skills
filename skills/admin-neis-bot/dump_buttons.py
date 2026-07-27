import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

opts = Options()
opts.add_experimental_option("debuggerAddress", "localhost:9222")
driver = webdriver.Chrome(options=opts)

handles = driver.window_handles
print(f"Handles: {handles}")

for handle in handles:
    driver.switch_to.window(handle)
    driver.switch_to.default_content()
    print(f"Window Title: {driver.title}")
    
    # Scan frames
    frames = driver.find_elements(By.TAG_NAME, "iframe")
    for i, frame in enumerate(frames):
        fid = frame.get_attribute("id") or frame.get_attribute("name") or f"index_{i}"
        try:
            driver.switch_to.default_content()
            driver.switch_to.frame(frame)
            has_cpr = driver.execute_script("return typeof cpr !== 'undefined';")
            if has_cpr:
                res = driver.execute_script("""
                    var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
                    var app = instances.find(ai => ai.app && ai.app.id !== "app/cmn/confirm" && ai.app.id !== "app/cmn/alert");
                    if (!app) return {error: "No app found in frame " + window.location.href};
                    
                    var buttons = [];
                    app.getContainer().getAllRecursiveChildren().forEach(function(ctrl) {
                        if (ctrl.type === "button" || ctrl.constructor.name.includes("Button")) {
                            buttons.push({
                                id: ctrl.id || "",
                                value: ctrl.value || "",
                                text: ctrl.text || "",
                                visible: ctrl.visible,
                                fieldLabel: ctrl.fieldLabel || ""
                            });
                        }
                    });
                    return {appId: app.app.id, buttons: buttons};
                """)
                print(f"  Frame '{fid}': {res}")
        except Exception as e:
            print(f"  Frame '{fid}' error: {e}")
