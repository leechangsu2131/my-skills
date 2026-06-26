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
                
    # Get subjects from cmbUdcAuth
    res = driver.execute_script(JS_FIND_APP + """
        var udc = inst.lookup("udcSbjt");
        if (!udc) return {error: "udcSbjt not found"};
        
        var emb = udc.getEmbeddedAppInstance();
        if (!emb) return {error: "Embedded app instance of udcSbjt not found"};
        
        var cmb = emb.lookup("cmbUdcAuth");
        if (!cmb) return {error: "cmbUdcAuth not found in embedded app"};
        
        var items = cmb.getItems();
        return items.map(function(it) {
            return {
                label: it.label,
                value: it.value
            };
        });
    """)
    
    if isinstance(res, dict) and "error" in res:
        print("Error:", res["error"])
        return
        
    # Decode string values to prevent terminal printing issues
    def decode_cpr_str(s: str) -> str:
        if not isinstance(s, str):
            return s
        try:
            return s.encode('latin1').decode('euc-kr')
        except Exception:
            return s
            
    print(f"Found {len(res)} subjects in cmbUdcAuth:")
    for idx, item in enumerate(res):
        label = decode_cpr_str(item["label"])
        value = decode_cpr_str(item["value"])
        print(f"  [{idx}] Label: '{label}' | Value: '{value}'")

if __name__ == "__main__":
    main()
