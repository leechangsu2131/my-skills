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
        print("NEIS app screen not found.")
        return

    # Switch to Math (수학)
    math_value = "0121621010103:0001000002:10051"
    d.execute_script(f"""
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var inst = instances.find(ai => ai.app && ai.app.id === "edu/sw/els/scr/es/els_scres00_m00");
        var udc = inst.lookup("udcSbjt");
        var embApp = udc.getEmbeddedAppInstance();
        var cmb = embApp.lookup("cmbUdcAuth");
        cmb.selectItemByValue("{math_value}");
    """)
    time.sleep(3)
    
    # Get realms
    realms = d.execute_script("""
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var inst = instances.find(ai => ai.app && ai.app.id === "edu/sw/els/scr/es/els_scres00_m00");
        var cmbRelm = inst.lookup("cmbRelm01");
        return cmbRelm.getItems().map(function(it) { return {label: it.label, value: it.value}; });
    """)
    
    print(f"Found {len(realms)} realms for 수학. Fetching standards for each...")
    
    math_standards = {}
    for r in realms:
        # Select realm
        d.execute_script(f"""
            var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
            var inst = instances.find(ai => ai.app && ai.app.id === "edu/sw/els/scr/es/els_scres00_m00");
            var cmbRelm = inst.lookup("cmbRelm01");
            cmbRelm.selectItemByValue("{r['value']}");
        """)
        time.sleep(1.5)
        
        # Get standards
        standards = d.execute_script("""
            var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
            var inst = instances.find(ai => ai.app && ai.app.id === "edu/sw/els/scr/es/els_scres00_m00");
            var cmbScces = inst.lookup("cmbSccesCtr");
            return cmbScces.getItems().map(function(it) { return {label: it.label, value: it.value}; });
        """)
        
        math_standards[r['label']] = standards
        print(f"Realm '{r['label']}' -> {len(standards)} standards")
        for s in standards:
            print(f"   - {s['label']}")
            
    # Save the standards mapping to scratch
    with open("scratch/math_standards.json", "w", encoding="utf-8") as f:
        json.dump(math_standards, f, ensure_ascii=False, indent=2)
    print("\nSaved math standards to scratch/math_standards.json")

if __name__ == "__main__":
    main()
