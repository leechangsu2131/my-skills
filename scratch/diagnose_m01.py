import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

def main():
    opts = Options()
    opts.add_experimental_option("debuggerAddress", "localhost:9222")
    driver = webdriver.Chrome(options=opts)
    
    JS_FIND_APP = """
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var inst = instances.find(ai => ai.app && ai.app.id.includes("els_sdlbg00_m01"));
        if (!inst) return null;
        return inst.app.id;
    """
    
    target_handle = None
    target_frame = None
    target_app = None
    
    handles = driver.window_handles
    for h in handles:
        driver.switch_to.window(h)
        driver.switch_to.default_content()
        try:
            has_cpr = driver.execute_script("return typeof cpr !== 'undefined';")
            if has_cpr:
                app_id = driver.execute_script(JS_FIND_APP)
                if app_id:
                    target_handle = h
                    target_frame = None
                    target_app = app_id
                    break
        except Exception:
            pass
            
        try:
            frames = driver.find_elements(By.TAG_NAME, "iframe")
            for i, f in enumerate(frames):
                fid = f.get_attribute("id") or f.get_attribute("name") or f"index_{i}"
                try:
                    driver.switch_to.default_content()
                    driver.switch_to.frame(f)
                    has_cpr = driver.execute_script("return typeof cpr !== 'undefined';")
                    if has_cpr:
                        app_id = driver.execute_script(JS_FIND_APP)
                        if app_id:
                            target_handle = h
                            target_frame = fid
                            target_app = app_id
                            break
                except Exception:
                    pass
        except Exception:
            pass
            
    if not target_handle:
        print("Error: App instance els_sdlbg00_m01 not found in any window/frame.")
        return
        
    print(f"Found els_sdlbg00_m01 in handle {target_handle}, frame {target_frame}")
    
    # Switch to target context
    driver.switch_to.window(target_handle)
    driver.switch_to.default_content()
    if target_frame:
        frames = driver.find_elements(By.TAG_NAME, "iframe")
        for f in frames:
            if f.get_attribute("id") == target_frame or f.get_attribute("name") == target_frame:
                driver.switch_to.frame(f)
                break
                
    # Run diagnosis
    JS_DIAGNOSE = """
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var inst = instances.find(ai => ai.app && ai.app.id.includes("els_sdlbg00_m01"));
        
        var dsResult = [];
        var dsNames = Object.keys(inst._dataModelMap || {});
        dsNames.forEach(function(name) {
            var dm = inst.lookup(name);
            if (!dm) return;
            var info = {id: name, type: dm.constructor.name || "unknown"};
            try { info.rowCount = dm.getRowCount(); } catch(e) { info.rowCount = null; }
            try {
                var headers = dm.getHeaders();
                var cols = [];
                for (var i = 0; i < headers.length; i++) cols.push(headers[i].getName());
                info.cols = cols;
            } catch(e) { info.cols = []; }
            if (info.rowCount > 0 && info.cols.length > 0) {
                var sample = {};
                for (var j = 0; j < info.cols.length; j++) {
                    try { sample[info.cols[j]] = dm.getValue(0, info.cols[j]); } catch(e) {}
                }
                info.sample = sample;
            }
            dsResult.push(info);
        });
        
        var controls = [];
        try {
            inst.getContainer().getAllRecursiveChildren().forEach(c => {
                controls.push({
                    id: c.id || "",
                    type: c.type || (c.constructor && c.constructor.name) || "",
                    fieldLabel: c.fieldLabel || "",
                    text: c.text || ""
                });
            });
        } catch(e) {}
        
        return {datasets: dsResult, controls: controls};
    """
    
    res = driver.execute_script(JS_DIAGNOSE)
    
    # helper function to decode euc-kr garbled strings
    def decode_cpr_str(s):
        if not isinstance(s, str):
            return s
        try:
            return s.encode('latin1').decode('euc-kr')
        except Exception:
            return s

    if isinstance(res, dict) and "datasets" in res:
        for ds in res["datasets"]:
            if "sample" in ds:
                for k, v in ds["sample"].items():
                    ds["sample"][k] = decode_cpr_str(v)
        for ctrl in res["controls"]:
            for k, v in ctrl.items():
                ctrl[k] = decode_cpr_str(v)
                
    print(json.dumps(res, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
