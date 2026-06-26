from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import json

REMOTE_PORT = 9222

JS_FIND_APP = """
    var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var inst = instances.find(ai => ai.app && ai.app.id.includes("scres10_m00"));
    if (!inst) return {error: "App instance scres10_m00 not found"};
"""

def main():
    opts = Options()
    opts.add_experimental_option("debuggerAddress", f"localhost:{REMOTE_PORT}")
    driver = webdriver.Chrome(options=opts)
    
    handles = driver.window_handles
    target_handle = None
    target_frame = None
    for handle in handles:
        driver.switch_to.window(handle)
        driver.switch_to.default_content()
        try:
            has_cpr = driver.execute_script("return typeof cpr !== 'undefined';")
            if has_cpr:
                app_info = driver.execute_script(JS_FIND_APP + "return {ok: true, appId: inst.app.id};")
                if "ok" in app_info:
                    target_handle = handle
                    target_frame = None
                    break
        except Exception:
            pass

        frames = driver.find_elements(by="tag name", value="iframe")
        for i, frame in enumerate(frames):
            fid = frame.get_attribute("id") or frame.get_attribute("name") or f"index_{i}"
            try:
                driver.switch_to.default_content()
                driver.switch_to.frame(frame)
                has_cpr = driver.execute_script("return typeof cpr !== 'undefined';")
                if has_cpr:
                    app_info = driver.execute_script(JS_FIND_APP + "return {ok: true, appId: inst.app.id};")
                    if "ok" in app_info:
                        target_handle = handle
                        target_frame = fid
                        break
            except Exception:
                pass
        if target_handle:
            break
            
    if not target_handle:
        print("Could not find NEIS app window/frame")
        return
        
    driver.switch_to.window(target_handle)
    driver.switch_to.default_content()
    if target_frame:
        frames = driver.find_elements(by="tag name", value="iframe")
        for frame in frames:
            if frame.get_attribute("id") == target_frame or frame.get_attribute("name") == target_frame:
                driver.switch_to.frame(frame)
                break
                
    # Dump columns safely
    res = driver.execute_script(JS_FIND_APP + """
        var ds = inst.lookup("dsMain");
        if (!ds) return {error: "dsMain not found"};
        if (ds.getRowCount() === 0) return {error: "dsMain has 0 rows"};
        
        var cols = [];
        try {
            var headers = ds.getHeaders();
            for (var i = 0; i < headers.length; i++) {
                cols.push(headers[i].getName());
            }
        } catch(e) {
            try {
                // Try to get headers by property scan
                for (var key in ds) {
                    if (typeof ds[key] === 'function' && (key.includes("Header") || key.includes("Col"))) {
                        // try to inspect
                    }
                }
            } catch(e2) {}
        }
        
        // If headers not found, fallback to checking getValue(0, colName) with trial and error or scanning columns
        if (cols.length === 0) {
            try {
                // eXbuilder6 DataSet Column layouts
                // Let's try column count
                var cc = ds.getColumnCount();
                for (var i = 0; i < cc; i++) {
                    cols.push(i); // just indices
                }
            } catch(e3) {}
        }
        
        var rowData = {};
        for (var i = 0; i < cols.length; i++) {
            var c = cols[i];
            try {
                rowData[c] = ds.getValue(0, c);
            } catch(e4) {
                rowData[c] = "error: " + e4.toString();
            }
        }
        
        return {cols: cols, rowData: rowData, rowCount: ds.getRowCount()};
    """)
    
    print(json.dumps(res, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
