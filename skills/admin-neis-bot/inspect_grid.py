from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import json
from pathlib import Path

def main():
    o = Options()
    o.add_experimental_option("debuggerAddress", "localhost:9222")
    driver = webdriver.Chrome(options=o)
    
    js = """
        const platform = window.cpr && cpr.core && cpr.core.Platform && cpr.core.Platform.INSTANCE;
        const app = platform.getAllRunningAppInstances().find(ai => ai.app && ai.app.id.includes('scres20_m00'));
        const grid = app.lookup('grdStdnt');
        if (!grid) return [];
        
        const methods = [];
        for (let prop in grid) {
            if (typeof grid[prop] === 'function') {
                methods.push(prop);
            }
        }
        return methods.sort();
    """
    methods = driver.execute_script(js)
    print("Grid Methods count:", len(methods))
    Path("scratch/grid_methods.json").write_text(json.dumps(methods, indent=2), encoding="utf-8")
    print("Methods written to scratch/grid_methods.json")

if __name__ == "__main__":
    main()
