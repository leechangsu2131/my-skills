from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

REMOTE_PORT = 9222

JS_FIND_APP = """
    var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var inst = instances.find(ai => ai.app && ai.app.id.includes("scres20_m00"));
    if (!inst) return {error: "App instance scres20_m00 not found"};
"""

def main():
    opts = Options()
    opts.add_experimental_option("debuggerAddress", f"localhost:{REMOTE_PORT}")
    driver = webdriver.Chrome(options=opts)
    
    target_handle = None
    target_frame = None
    
    handles = driver.window_handles
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
                
    # List all grids and their content
    grids_info = driver.execute_script("""
        var grids = document.querySelectorAll('.cl-grid');
        var res = [];
        for (var i = 0; i < grids.length; i++) {
            var g = grids[i];
            var id = g.id || "";
            var uuid = g.getAttribute("uuid") || "";
            
            // Get all texts inside this grid
            var texts = [];
            var els = g.querySelectorAll('.cl-text, td, span, div');
            for (var j = 0; j < els.length; j++) {
                var txt = (els[j].innerText || els[j].textContent || "").trim();
                if (txt && !texts.includes(txt) && txt.length < 30) {
                    texts.push(txt);
                }
            }
            res.push({
                index: i,
                id: id,
                uuid: uuid,
                className: g.className,
                textCount: texts.length,
                texts: texts.slice(0, 20)
            });
        }
        return res;
    """)
    
    print(f"Found {len(grids_info)} grids in the active document:")
    for g in grids_info:
        print(f"\nGrid Index: {g['index']} | ID: '{g['id']}' | UUID: '{g['uuid']}' | Class: '{g['className']}'")
        print(f"  Texts count: {g['textCount']}")
        print(f"  Sample texts: {g['texts']}")

if __name__ == "__main__":
    main()
