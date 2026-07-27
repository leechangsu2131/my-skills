import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

REMOTE_PORT = 9222

JS_DIAGNOSE_ALL = """
return (function() {
  const platform = window.cpr && cpr.core && cpr.core.Platform && cpr.core.Platform.INSTANCE;
  if (!platform) return {error: "window.cpr Platform is not available"};
  
  const apps = platform.getAllRunningAppInstances().map((ai, idx) => {
    const controls = [];
    const datasets = [];
    try {
      ai.getContainer().getAllRecursiveChildren().forEach(c => {
        controls.push({
          id: c.id || "",
          type: c.type || (c.constructor && c.constructor.name) || "",
          fieldLabel: c.fieldLabel || "",
          text: c.text || "",
          value: typeof c.value !== "undefined" ? c.value : null
        });
      });
    } catch (e) {
      controls.push({error: String(e)});
    }
    
    try {
      const dataControls = ai.getAllDataControls ? ai.getAllDataControls() : [];
      dataControls.forEach(ds => {
        const cols = [];
        try {
          for (let i = 0; i < ds.getColumnCount(); i++) {
            const c = ds.getColumn(i);
            cols.push(c && (c.columnName || c.name || String(c)));
          }
        } catch (e) {}
        
        datasets.push({
          id: ds.id || "",
          type: ds.type || (ds.constructor && ds.constructor.name) || "",
          rowCount: ds.getRowCount ? ds.getRowCount() : null,
          cols: cols.filter(Boolean),
          sample: ds.getRowCount && ds.getRowCount() ? cols.slice(0, 10).reduce((o, col) => {
            try { o[col] = ds.getValue(0, col); } catch(e) {}
            return o;
          }, {}) : {}
        });
      });
    } catch (e) {
      datasets.push({error: String(e)});
    }
    
    return {idx, appId: ai.app && ai.app.id, title: ai.title || "", controlsCount: controls.length, datasets};
  });
  return {apps};
})();
"""

def main():
    opts = Options()
    opts.add_experimental_option("debuggerAddress", f"localhost:{REMOTE_PORT}")
    driver = webdriver.Chrome(options=opts)
    
    print(f"[connect] Connected to Chrome: {driver.title}")
    
    handles = driver.window_handles
    found = False
    
    for handle in handles:
        driver.switch_to.window(handle)
        driver.switch_to.default_content()
        
        # Check main page
        try:
            has_cpr = driver.execute_script("return typeof cpr !== 'undefined';")
            if has_cpr:
                res = driver.execute_script(JS_DIAGNOSE_ALL)
                print(f"\n--- Window '{driver.title}' (Main Frame) ---")
                print(json.dumps(res, ensure_ascii=False, indent=2))
                found = True
        except Exception as e:
            print(f"Error checking window {handle} main frame: {e}")
            
        # Check frames
        try:
            frames = driver.find_elements(by="tag name", value="iframe")
            for i, frame in enumerate(frames):
                fid = frame.get_attribute("id") or frame.get_attribute("name") or f"index_{i}"
                driver.switch_to.default_content()
                driver.switch_to.frame(frame)
                has_cpr = driver.execute_script("return typeof cpr !== 'undefined';")
                if has_cpr:
                    res = driver.execute_script(JS_DIAGNOSE_ALL)
                    print(f"\n--- Window '{driver.title}' (Frame: {fid}) ---")
                    print(json.dumps(res, ensure_ascii=False, indent=2))
                    found = True
        except Exception as e:
            print(f"Error checking frames in window {handle}: {e}")
            
    if not found:
        print("No cpr platform found in any window or frame.")

if __name__ == "__main__":
    main()
