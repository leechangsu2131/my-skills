import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def main():
    opts = Options()
    opts.add_experimental_option("debuggerAddress", "localhost:9222")
    driver = webdriver.Chrome(options=opts)
    
    # Target handle
    handles = driver.window_handles
    for h in handles:
        driver.switch_to.window(h)
        driver.switch_to.default_content()
        try:
            has_cpr = driver.execute_script("return typeof cpr !== 'undefined';")
            if has_cpr:
                app_id = driver.execute_script("return cpr.core.Platform.INSTANCE.getAllRunningAppInstances().map(ai => ai.app.id).find(id => id.includes('els_sdlbg00_m01'));")
                if app_id:
                    break
        except Exception:
            pass
            
    print(f"Connected to {driver.title}")
    
    JS_FIND_APP = """
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var inst = instances.find(ai => ai.app && ai.app.id.includes("els_sdlbg00_m01"));
    """
    
    # Select index 1 (김가을)
    print("Selecting index 1 (김가을)...")
    driver.execute_script(JS_FIND_APP + "inst.lookup('grdStu').selectRows([1]);")
    time.sleep(1.5)
    
    # Revert first if modified
    driver.execute_script(JS_FIND_APP + "var ds = inst.lookup('dsGicRecStu'); if(ds) ds.revert();")
    time.sleep(0.5)
    
    # Add a row
    print("Adding a row...")
    driver.execute_script(JS_FIND_APP + "inst.lookup('btnAdd').click();")
    time.sleep(0.5)
    
    # Set values
    driver.execute_script(JS_FIND_APP + """
        var ds = inst.lookup("dsGicRecStu");
        ds.setValue(ds.getRowCount() - 1, "ghvrDevEnfcYmd", "20260316");
        ds.setValue(ds.getRowCount() - 1, "ghvrDevCn", "저장 테스트용 내용");
        inst.lookup("grdGicRecStu").redraw();
    """)
    
    # Click save
    print("Clicking btnSaveStu...")
    driver.execute_script(JS_FIND_APP + "inst.lookup('btnSaveStu').click();")
    
    # Monitor running apps and print them every second for 8 seconds
    for sec in range(1, 9):
        time.sleep(1)
        apps = driver.execute_script("""
            return cpr.core.Platform.INSTANCE.getAllRunningAppInstances().map(ai => ai.app.id);
        """)
        is_modified = driver.execute_script(JS_FIND_APP + """
            var ds = inst.lookup("dsGicRecStu");
            return ds ? ds.isModified() : false;
        """)
        print(f"[{sec}s] Running apps: {apps} | dsGicRecStu.isModified() = {is_modified}")
        
        # Try dismissing any confirm or alert app
        driver.execute_script("""
            var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
            var modals = instances.filter(ai => ai && ai.app && (ai.app.id === "app/cmn/confirm" || ai.app.id === "app/cmn/alert"));
            modals.forEach(function(m) {
                try {
                    var container = m.getContainer();
                    if (!container) return;
                    var clicked = false;
                    function scan(ctrl) {
                        if (!ctrl || clicked) return;
                        var id = ctrl.id || "";
                        var val = ctrl.value || ctrl.text || "";
                        if (id === "btnOk" || id === "btnConfirm" || val === "확인" || val === "예" || val === "OK") {
                            if (typeof ctrl.click === 'function') {
                                try { ctrl.click(); clicked = true; console.log("Clicked confirm/alert OK"); } catch(e) {}
                            }
                        }
                        if (typeof ctrl.getChildren === 'function') {
                            var ch = ctrl.getChildren();
                            for (var j = 0; j < ch.length; j++) scan(ch[j]);
                        }
                    }
                    scan(container);
                } catch(e) {}
            });
        """)

if __name__ == "__main__":
    main()
