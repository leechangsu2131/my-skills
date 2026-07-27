import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

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
                
    # Get HTML element of grdStdnt and list all texts inside it
    res = driver.execute_script(JS_FIND_APP + """
        var grid = inst.lookup("grdStdnt");
        if (!grid) return {error: "grdStdnt not found"};
        
        var el = grid.getHtmlElement();
        if (!el) return {error: "grdStdnt has no html element"};
        
        // Find all elements with text inside grdStdnt's DOM
        var descendants = el.querySelectorAll('*');
        var texts = [];
        for (var i = 0; i < descendants.length; i++) {
            var d = descendants[i];
            var txt = (d.innerText || d.textContent || "").trim();
            if (txt && txt.length > 0 && txt.length < 50) {
                texts.push({
                    tagName: d.tagName,
                    className: d.className,
                    text: txt
                });
            }
        }
        return {
            gridId: grid.id,
            gridUuid: grid.uuid || "",
            className: el.className,
            texts: texts
        };
    """)
    
    if "error" in res:
        print("Error:", res["error"])
        return
        
    print(f"Grid ID: {res['gridId']} | Uuid: {res['gridUuid']} | Class: {res['className']}")
    print(f"Found {len(res['texts'])} elements with text inside grdStdnt:")
    for idx, t in enumerate(res["texts"]):
        text = t["text"]
        # Print actual codepoints to avoid console print issues
        codepoints = [f"U+{ord(c):04X}" for c in text]
        print(f"  [{idx}] Tag={t['tagName']} Class={t['className']}")
        print(f"      Text: {text}")
        print(f"      Codepoints: {' '.join(codepoints)}")

if __name__ == "__main__":
    main()
