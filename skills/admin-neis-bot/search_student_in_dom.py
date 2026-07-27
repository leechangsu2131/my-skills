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
                
    # Search in DOM using JS
    res = driver.execute_script("""
        var allElements = document.getElementsByTagName('*');
        var results = [];
        for (var i = 0; i < allElements.length; i++) {
            var el = allElements[i];
            var html = el.innerHTML || "";
            // Check if it contains '시우' or '가을'
            if (html.includes('시우') || html.includes('가을')) {
                // If it is a leaf element containing the text (no children containing it)
                var hasChildWithText = false;
                for (var j = 0; j < el.children.length; j++) {
                    var childHtml = el.children[j].innerHTML || "";
                    if (childHtml.includes('시우') || childHtml.includes('가을')) {
                        hasChildWithText = true;
                        break;
                    }
                }
                if (!hasChildWithText) {
                    results.push({
                        tagName: el.tagName,
                        className: el.className,
                        text: (el.innerText || el.textContent || "").trim(),
                        outerHTML: el.outerHTML.slice(0, 300)
                    });
                }
            }
        }
        return results;
    """)
    
    print(f"Found {len(res)} matching leaf elements in DOM:")
    for idx, item in enumerate(res[:30]):
        print(f"\n[{idx}] Tag: {item['tagName']} | Class: {item['className']}")
        print(f"    Text: {item['text']}")
        print(f"    HTML: {item['outerHTML']}")

if __name__ == "__main__":
    main()
