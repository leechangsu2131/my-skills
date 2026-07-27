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
        print(f"Failed to connect to Chrome: {e}")
        return

    # Find the NEIS app window
    found_handle = None
    for h in d.window_handles:
        try:
            d.switch_to.window(h)
            has_cpr = d.execute_script("return typeof cpr !== 'undefined';")
            if has_cpr:
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
                    found_handle = h
                    break
        except Exception:
            pass

    if not found_handle:
        print("NEIS app screen not found. Make sure you are on the Evaluation screen.")
        return

    print(f"Connected to NEIS app window: {d.title}")
    
    # Try switching to Moral Education (도덕)
    # Value: "0121621010102:0001000007:10048"
    dodeok_value = "0121621010102:0001000007:10048"
    
    switch_res = d.execute_script(f"""
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var inst = instances.find(ai => ai.app && ai.app.id === "edu/sw/els/scr/es/els_scres00_m00");
        
        var udc = inst.lookup("udcSbjt");
        var embApp = udc.getEmbeddedAppInstance();
        var cmb = embApp.lookup("cmbUdcAuth");
        
        // Select the subject in the internal combo
        cmb.selectItemByValue("{dodeok_value}");
        
        return {{
            selectedLabel: cmb.getSelectionFirst() ? cmb.getSelectionFirst().label : "none",
            selectedValue: cmb.value || "",
            udcValue: udc.getValue(),
            udcText: udc.getText()
        }};
    """)
    
    print("\nSubject switch triggered inside UDC:")
    print(json.dumps(switch_res, ensure_ascii=False, indent=2))
    
    # Wait for 3 seconds for NEIS to request and update realms/standards
    print("Waiting 3 seconds for UI updates...")
    time.sleep(3)
    
    # Fetch realms and standards to verify they updated
    ui_state = d.execute_script("""
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var inst = instances.find(ai => ai.app && ai.app.id === "edu/sw/els/scr/es/els_scres00_m00");
        
        var cmbRelm = inst.lookup("cmbRelm01");
        var cmbScces = inst.lookup("cmbSccesCtr");
        
        var realms = cmbRelm.getItems().map(function(it) { return {label: it.label, value: it.value}; });
        var standards = cmbScces.getItems().map(function(it) { return {label: it.label, value: it.value}; });
        
        return {
            realms: realms,
            standards: standards
        };
    """)
    
    print("\n=== Current Realms in Dropdown ===")
    for r in ui_state["realms"]:
        print(f" - {r['label']} (value={r['value']})")
        
    print("\n=== Current Standards in Dropdown ===")
    for s in ui_state["standards"]:
        print(f" - {s['label']} (value={s['value']})")

if __name__ == "__main__":
    main()
