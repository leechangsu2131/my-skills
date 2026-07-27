import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def main():
    o = Options()
    o.add_experimental_option("debuggerAddress", "localhost:9222")
    d = webdriver.Chrome(options=o)
    
    # Switch to Social Studies (사회)
    social_value = "0121621010102:0001000006:10045"
    d.execute_script(f"""
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var inst = instances.find(ai => ai.app && ai.app.id === "edu/sw/els/scr/es/els_scres00_m00");
        var udc = inst.lookup("udcSbjt");
        var embApp = udc.getEmbeddedAppInstance();
        var cmb = embApp.lookup("cmbUdcAuth");
        cmb.selectItemByValue("{social_value}", true);
    """)
    time.sleep(3)
    
    # 1. Try selecting '역사' (value='3') WITH emitEvent=true
    d.execute_script("""
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var inst = instances.find(ai => ai.app && ai.app.id === "edu/sw/els/scr/es/els_scres00_m00");
        var cmbRelm = inst.lookup("cmbRelm01");
        cmbRelm.selectItemByValue("3", true); // Select '역사' and trigger events
    """)
    print("Selecting '역사' with event emit...")
    time.sleep(3)
    
    # 2. Get current standards dropdown items
    standards = d.execute_script("""
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var inst = instances.find(ai => ai.app && ai.app.id === "edu/sw/els/scr/es/els_scres00_m00");
        var cmbScces = inst.lookup("cmbSccesCtr");
        return cmbScces.getItems().map(function(it) { return {label: it.label, value: it.value}; });
    """)
    
    print("\n=== Standards for 역사 (History) ===")
    for s in standards:
        print(f" - {s['label']} (value={s['value']})")

if __name__ == "__main__":
    main()
