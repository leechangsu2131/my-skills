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
    
    # Dismiss all modals first
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
                            try { ctrl.click(); clicked = true; } catch(e) {}
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
    print("Modals dismissed.")
    time.sleep(1)
    
    # Revert dataset
    driver.execute_script("""
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var inst = instances.find(ai => ai.app && ai.app.id.includes("els_sdlbg00_m01"));
        if (inst) {
            var ds = inst.lookup("dsGicRecStu");
            if (ds) ds.revert();
            var grid = inst.lookup("grdGicRecStu");
            if (grid) grid.redraw();
        }
    """)
    print("Dataset changes reverted.")

if __name__ == "__main__":
    main()
