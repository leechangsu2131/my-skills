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
                
    # Inspect dsScrOsuCd and UDC controls
    res = driver.execute_script(JS_FIND_APP + """
        var ds = inst.lookup("dsScrOsuCd");
        if (!ds) return {error: "dsScrOsuCd not found"};
        
        var subjects = [];
        for (var i = 0; i < ds.getRowCount(); i++) {
            var headers = ds.getHeaders ? ds.getHeaders() : [];
            var colNames = headers.map(h => h.getName());
            if (colNames.length === 0) colNames = ["cd", "nm", "value", "label"]; // guess
            
            // Let's get row values
            var row = {};
            for (var j = 0; j < ds.getColumnCount(); j++) {
                var c = ds.getColumnHeader ? ds.getColumnHeader(j) : j;
                try {
                    row[c] = ds.getValue(i, c);
                } catch(e) {
                    try {
                        row[j] = ds.getValue(i, j);
                    } catch(e2) {}
                }
            }
            subjects.push(row);
        }
        
        // Find UDC subject combo
        // Let's list all UDC/combobox controls in the container
        var udcControls = [];
        inst.getContainer().getAllRecursiveChildren().forEach(function(c) {
            var type = c.type || (c.constructor && c.constructor.name) || "";
            if (type.includes("Combo") || type.includes("udc") || c.id === "udcSbjt") {
                udcControls.push({
                    id: c.id || "",
                    type: type,
                    fieldLabel: c.fieldLabel || "",
                    value: typeof c.getValue === 'function' ? c.getValue() : null,
                    text: typeof c.getText === 'function' ? c.getText() : null
                });
            }
        });
        
        return {subjects: subjects, udcControls: udcControls};
    """)
    
    # Decode string values to prevent terminal printing issues
    def decode_cpr_str(s: str) -> str:
        if not isinstance(s, str):
            return s
        try:
            return s.encode('latin1').decode('euc-kr')
        except Exception:
            return s
            
    print("Subjects from dsScrOsuCd:")
    for idx, s in enumerate(res.get("subjects", [])):
        decoded_s = {k: decode_cpr_str(v) for k, v in s.items()}
        print(f"  [{idx}] {decoded_s}")
        
    print("\nUDC / Combobox Controls:")
    for idx, c in enumerate(res.get("udcControls", [])):
        print(f"  [{idx}] ID: {c['id']} | Type: {c['type']} | Label: {decode_cpr_str(c['fieldLabel'])} | Value: {decode_cpr_str(c['value'])} | Text: {decode_cpr_str(c['text'])}")

if __name__ == "__main__":
    main()
