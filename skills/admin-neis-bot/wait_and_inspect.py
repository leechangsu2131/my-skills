import json
import time
import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def main():
    o = Options()
    o.add_experimental_option("debuggerAddress", "localhost:9222")
    try:
        d = webdriver.Chrome(options=o)
    except Exception as e:
        print(f"Failed to connect to Chrome: {e}")
        return

    print("Connected to Chrome. Searching for NEIS app instance...")
    
    start_time = time.time()
    found = False
    
    # Wait up to 5 minutes
    while time.time() - start_time < 300:
        handles = d.window_handles
        for h in handles:
            try:
                d.switch_to.window(h)
                # Check if cpr is defined
                has_cpr = d.execute_script("return typeof cpr !== 'undefined';")
                if has_cpr:
                    # Check if our evaluation app is running
                    app_exists = d.execute_script("""
                        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
                        for (var i = 0; i < instances.length; i++) {
                            if (instances[i].app && instances[i].app.id === "edu/sw/els/scr/es/els_scres00_m00") {
                                return true;
                            }
                        }
                        return false;
                    """)
                    if app_exists:
                        print(f"Found NEIS Evaluation App in window '{d.title}' (Handle: {h})!")
                        found = True
                        break
            except Exception as e:
                # Some handles might be closed or restricted
                pass
        
        if found:
            break
            
        print("Still waiting for NEIS Evaluation Screen... (Please log in and open: 학급담임 > 성적 > 학생평가 > 교과평가 > 성취기준별 평가)")
        time.sleep(5)
        
    if not found:
        print("Timeout waiting for NEIS Evaluation Screen.")
        return

    # Now inspect the udcSbjt control
    inspect_script = """
    var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var inst = null;
    for (var i = 0; i < instances.length; i++) {
        if (instances[i].app && instances[i].app.id === "edu/sw/els/scr/es/els_scres00_m00") {
            inst = instances[i];
            break;
        }
    }
    
    var udc = inst.lookup("udcSbjt");
    if (!udc) return {error: "udcSbjt not found"};
    
    var embApp = udc.getEmbeddedAppInstance();
    if (!embApp) return {error: "Embedded app instance not found"};
    
    // Find all controls recursively in the embedded app
    var uiControls = [];
    function scanControls(ctrl) {
        if (!ctrl) return;
        var id = ctrl.id || "";
        var type = ctrl.constructor ? ctrl.constructor.name : "?";
        var info = {id: id, type: type};
        
        if (typeof ctrl.getItems === 'function') {
            try {
                info.items = ctrl.getItems().map(function(it) {
                    return {label: it.label, value: it.value};
                });
            } catch(e) {}
        }
        uiControls.push(info);
        
        if (typeof ctrl.getChildren === 'function') {
            try {
                var ch = ctrl.getChildren();
                for (var i = 0; i < ch.length; i++) {
                    scanControls(ch[i]);
                }
            } catch(e) {}
        }
    }
    scanControls(embApp.getContainer());
    
    return {
        udcType: udc.constructor ? udc.constructor.name : "?",
        uiControls: uiControls
    };
    """
    
    try:
        info = d.execute_script(inspect_script)
        print("\\n=== UDC Inspection Results ===")
        print(json.dumps(info, ensure_ascii=False, indent=2))
        
        # Write to scratch file for reference
        with open("scratch/udc_inspection.json", "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)
        print("Saved results to scratch/udc_inspection.json")
    except Exception as e:
        print(f"Failed to inspect UDC: {e}")

if __name__ == "__main__":
    main()
