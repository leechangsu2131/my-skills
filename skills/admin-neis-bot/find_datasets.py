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
                            break
                except Exception:
                    pass
        except Exception:
            pass
            
    if not target_handle:
        print("Error: App instance els_sdlbg00_m01 not found.")
        return
        
    driver.switch_to.window(target_handle)
    driver.switch_to.default_content()
    if target_frame:
        frames = driver.find_elements(By.TAG_NAME, "iframe")
        for f in frames:
            if f.get_attribute("id") == target_frame or f.get_attribute("name") == target_frame:
                driver.switch_to.frame(f)
                break
                
    JS_FIND_DATASETS = """
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var inst = instances.find(ai => ai.app && ai.app.id.includes("els_sdlbg00_m01"));
        
        var dsResult = [];
        // Scan inst properties and lookups
        var keys = Object.keys(inst);
        
        // Helper to extract dataset info
        function getDsInfo(name, dm) {
            if (!dm || typeof dm.getRowCount !== 'function') return null;
            var info = {id: name, type: dm.constructor.name || "unknown"};
            try { info.rowCount = dm.getRowCount(); } catch(e) {}
            try {
                var headers = dm.getHeaders();
                var cols = [];
                for (var i = 0; i < headers.length; i++) cols.push(headers[i].getName());
                info.cols = cols;
            } catch(e) {}
            if (info.rowCount > 0 && info.cols.length > 0) {
                var sample = {};
                for (var j = 0; j < info.cols.length; j++) {
                    try { sample[info.cols[j]] = dm.getValue(0, info.cols[j]); } catch(e) {}
                }
                info.sample = sample;
            }
            return info;
        }

        // Search container controls for bound datasets
        inst.getContainer().getAllRecursiveChildren().forEach(c => {
            if (c.dataSet) {
                var dsInfo = getDsInfo(c.dataSet.id || "bound_ds", c.dataSet);
                if (dsInfo && !dsResult.some(r => r.id === dsInfo.id)) {
                    dsResult.push(dsInfo);
                }
            }
        });
        
        // Also check default dataModelMap properties
        if (inst._dataModelMap) {
            Object.keys(inst._dataModelMap).forEach(k => {
                var dm = inst.lookup(k);
                var dsInfo = getDsInfo(k, dm);
                if (dsInfo && !dsResult.some(r => r.id === dsInfo.id)) {
                    dsResult.push(dsInfo);
                }
            });
        }
        
        return dsResult;
    """
    
    res = driver.execute_script(JS_FIND_DATASETS)
    
    # helper function to decode euc-kr garbled strings
    def decode_cpr_str(s):
        if not isinstance(s, str):
            return s
        try:
            return s.encode('latin1').decode('euc-kr')
        except Exception:
            return s

    for ds in res:
        if "sample" in ds:
            for k, v in ds["sample"].items():
                ds["sample"][k] = decode_cpr_str(v)
                
    print(json.dumps(res, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
