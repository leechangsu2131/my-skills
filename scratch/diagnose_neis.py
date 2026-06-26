import json
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

REMOTE_PORT = 9222

JS_DIAGNOSE = r"""
return (function() {
  function valueAt(ds, row, col) {
    try { return ds.getValue(row, col); } catch (e) { return null; }
  }
  function getCols(ds) {
    const cols = [];
    try {
      for (let i = 0; i < ds.getColumnCount(); i++) {
        const c = ds.getColumn(i);
        cols.push(c && (c.columnName || c.name || String(c)));
      }
    } catch (e) {}
    return cols.filter(Boolean);
  }
  const platform = window.cpr && cpr.core && cpr.core.Platform && cpr.core.Platform.INSTANCE;
  if (!platform) return null;
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
          value: typeof c.value !== "undefined" ? c.value : null,
          itemCount: c.getItemCount ? c.getItemCount() : null
        });
      });
    } catch (e) {
      controls.push({error: String(e)});
    }
    try {
      const dataControls = ai.getAllDataControls ? ai.getAllDataControls() : [];
      dataControls.forEach(ds => {
        const cols = getCols(ds);
        datasets.push({
          id: ds.id || "",
          type: ds.type || (ds.constructor && ds.constructor.name) || "",
          rowCount: ds.getRowCount ? ds.getRowCount() : null,
          cols,
          sample: ds.getRowCount && ds.getRowCount() > 0 ? cols.slice(0, 10).reduce((o, col) => {
            o[col] = valueAt(ds, 0, col);
            return o;
          }, {}) : {}
        });
      });
    } catch (e) {
      datasets.push({error: String(e)});
    }
    return {idx, appId: ai.app && ai.app.id, title: ai.title || "", controls, datasets};
  });
  return {apps};
})();
"""

def main():
    opts = Options()
    opts.add_experimental_option("debuggerAddress", f"localhost:{REMOTE_PORT}")
    driver = webdriver.Chrome(options=opts)
    print(f"Connected to browser: {driver.title}")

    results = {}
    
    handles = driver.window_handles
    print(f"Total window handles: {len(handles)}")
    
    for h_idx, handle in enumerate(handles):
        driver.switch_to.window(handle)
        w_title = driver.title
        print(f"--- Window {h_idx}: '{w_title}' ---")
        
        # 1. Main frame
        driver.switch_to.default_content()
        try:
            res = driver.execute_script(JS_DIAGNOSE)
            if res:
                results[f"win_{h_idx}_main"] = res
                print(f"Found cpr app in win_{h_idx}_main")
        except Exception as e:
            print(f"Error on win_{h_idx}_main: {e}")

        # 2. Iterate frames
        frames = driver.find_elements(By.TAG_NAME, "iframe")
        print(f"Found {len(frames)} frames in win_{h_idx}")
        for i, frame in enumerate(frames):
            fid = frame.get_attribute("id") or frame.get_attribute("name") or f"index_{i}"
            try:
                driver.switch_to.default_content()
                driver.switch_to.frame(frame)
                res = driver.execute_script(JS_DIAGNOSE)
                if res:
                    results[f"win_{h_idx}_frame_{fid}"] = res
                    print(f"Found cpr app in win_{h_idx}_frame_{fid}'")
            except Exception as e:
                print(f"Error on win_{h_idx}_frame_{fid}': {e}")
            
    # Return to main
    driver.switch_to.default_content()

    output_path = Path("scratch/frame_diagnose.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Diagnostic results saved to {output_path}")

    # Print summary
    for fid, res in results.items():
        print(f"\nFrame: {fid}")
        for app in res.get("apps", []):
            print(f"  App: {app['appId']} (Title: {app['title']})")
            for ds in app.get("datasets", []):
                print(f"    Dataset: {ds['id']} (Rows: {ds['rowCount']})")
                print(f"      Columns: {ds['cols']}")
                print(f"      Sample: {ds['sample']}")
            for ctl in app.get("controls", []):
                if ctl.get("id") in ["btnSearch", "btnSave", "grdMain", "dsMain", "cmbSbjt"]:
                    print(f"    Control: {ctl}")

if __name__ == "__main__":
    main()
