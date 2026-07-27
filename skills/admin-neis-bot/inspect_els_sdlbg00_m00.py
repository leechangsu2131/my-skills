import time
import json
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

REMOTE_PORT = 9222

JS_INSPECT = """
var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
var inst = instances.find(ai => ai.app && ai.app.id === "edu/sw/els/sdl/bg/els_sdlbg00_m00");
if (!inst) return {error: "App instance edu/sw/els/sdl/bg/els_sdlbg00_m00 not found"};

function getDsInfo(ds) {
    if (!ds) return null;
    var realCols = [];
    try {
        if (typeof ds.getColumnNames === 'function') {
            realCols = ds.getColumnNames();
        } else if (ds.getHeaders) {
            realCols = ds.getHeaders().map(h => h.getName());
        }
    } catch(e) {}
    
    var rows = [];
    for (var i = 0; i < ds.getRowCount(); i++) {
        var row = {};
        realCols.forEach(col => {
            try { row[col] = ds.getValue(i, col); } catch(e) {}
        });
        rows.push(row);
    }
    
    return {
        id: ds.id,
        rowCount: ds.getRowCount(),
        columns: realCols,
        rows: rows
    };
}

// Find all controls
var controls = [];
inst.getContainer().getAllRecursiveChildren().forEach(function(c) {
    var type = c.type || (c.constructor && c.constructor.name) || "";
    controls.push({
        id: c.id || "",
        type: type,
        fieldLabel: c.fieldLabel || "",
        text: c.text || "",
        value: typeof c.getValue === 'function' ? c.getValue() : null,
        visible: c.visible
    });
});

return {
    appId: inst.app.id,
    dsScrgRec: getDsInfo(inst.lookup("dsScrgRec")),
    dsActnSpecl: getDsInfo(inst.lookup("dsActnSpecl")),
    controls: controls
};
"""

def decode_cpr_str(s):
    if not isinstance(s, str):
        return s
    try:
        return s.encode('latin1').decode('euc-kr')
    except Exception:
        return s

def recursive_decode(data):
    if isinstance(data, dict):
        return {k: recursive_decode(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [recursive_decode(x) for x in data]
    elif isinstance(data, str):
        return decode_cpr_str(data)
    else:
        return data

def scan_frames_recursively(driver, frame_path=[]):
    # Check current context
    try:
        has_cpr = driver.execute_script("return typeof cpr !== 'undefined';")
        if has_cpr:
            res = driver.execute_script(JS_INSPECT)
            if res and "error" not in res:
                print(f"[success] Found at frame path: {frame_path}")
                return res
    except Exception:
        pass

    # Find child frames
    try:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
    except Exception:
        return None

    for i, frame in enumerate(iframes):
        fid = frame.get_attribute("id") or frame.get_attribute("name") or f"index_{i}"
        try:
            driver.switch_to.frame(frame)
            res = scan_frames_recursively(driver, frame_path + [fid])
            if res:
                return res
            driver.switch_to.parent_frame()
        except Exception:
            # If switch fails or recursive search fails, make sure we go back to parent context if possible
            try:
                driver.switch_to.parent_frame()
            except Exception:
                pass
    return None

def main():
    opts = Options()
    opts.add_experimental_option("debuggerAddress", f"localhost:{REMOTE_PORT}")
    driver = webdriver.Chrome(options=opts)
    
    handles = driver.window_handles
    for handle in handles:
        driver.switch_to.window(handle)
        driver.switch_to.default_content()
        print(f"Scanning window: '{driver.title}' ({handle})")
        res = scan_frames_recursively(driver)
        if res:
            decoded = recursive_decode(res)
            # Write to a file for easy reading
            Path("scratch/inspected_app_data.json").write_text(json.dumps(decoded, ensure_ascii=False, indent=2), encoding="utf-8")
            print("Successfully wrote scratch/inspected_app_data.json")
            return
            
    print("Could not find active window with app edu/sw/els/sdl/bg/els_sdlbg00_m00")

if __name__ == "__main__":
    main()
