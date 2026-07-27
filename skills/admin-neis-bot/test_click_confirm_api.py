import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def main():
    o = Options()
    o.add_experimental_option("debuggerAddress", "localhost:9222")
    try:
        d = webdriver.Chrome(options=o)
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    # Loop through window handles to find the NEIS app
    found_handle = None
    for h in d.window_handles:
        try:
            d.switch_to.window(h)
            has_cpr = d.execute_script("return typeof cpr !== 'undefined';")
            if has_cpr:
                found_handle = h
                break
        except Exception:
            pass

    if not found_handle:
        print("NEIS window not found.")
        return

    # eXBuilder specific dialog click script
    click_script = """
    var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var confirmApp = instances.find(ai => ai.app && (ai.app.id === "app/cmn/confirm" || ai.app.id === "app/cmn/alert"));
    if (!confirmApp) return {error: "No app/cmn/confirm or app/cmn/alert instance found"};
    
    var container = confirmApp.getContainer();
    if (!container) return {error: "Container not found"};
    
    var clicked = false;
    var clickedCtrl = null;
    
    function findAndClick(ctrl) {
        if (!ctrl || clicked) return;
        var type = ctrl.constructor ? ctrl.constructor.name : "";
        var val = ctrl.value || ctrl.text || "";
        var id = ctrl.id || "";
        
        // Match buttons with label '확인' or '예' or common confirm IDs
        if (id === "btnOk" || id === "btnConfirm" || val === "확인" || val === "예" || val === "OK") {
            if (typeof ctrl.click === 'function') {
                ctrl.click();
                clicked = true;
                clickedCtrl = {id: id, type: type, value: val};
                return;
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
    return {clicked: clicked, control: clickedCtrl};
    """
    
    res = d.execute_script(click_script)
    print("\n=== Dialog Click Result ===")
    print(json.dumps(res, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
