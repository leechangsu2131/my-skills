import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def main():
    opts = Options()
    opts.add_experimental_option("debuggerAddress", "localhost:9222")
    driver = webdriver.Chrome(options=opts)
    
    # Target handle
    handles = driver.window_handles
    for h in handles:
        driver.switch_to.window(h)
        driver.switch_to.default_content()
        try:
            has_cpr = driver.execute_script("return typeof cpr !== 'undefined';")
            if has_cpr:
                app_id = driver.execute_script("return cpr.core.Platform.INSTANCE.getAllRunningAppInstances().map(ai => ai.app.id).find(id => id.includes('els_sdlbg00_m01'));")
                if app_id:
                    break
        except Exception:
            pass
            
    print(f"Connected to {driver.title}")
    
    JS_FIND_APP = """
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var inst = instances.find(ai => ai.app && ai.app.id.includes("els_sdlbg00_m01"));
    """
    
    # Get current selected student name
    name_before = driver.execute_script(JS_FIND_APP + """
        var grid = inst.lookup("grdStu");
        var selectedIndices = grid.getSelectedRowIndices();
        if (selectedIndices.length > 0) {
            var ds = inst.lookup("dsStu");
            return ds.getValue(selectedIndices[0], "stuFlnm");
        }
        return "None";
    """)
    print(f"Selected student before: {name_before}")
    
    # Try selecting index 1 (김가을)
    print("Selecting index 1 (김가을)...")
    driver.execute_script(JS_FIND_APP + """
        var grid = inst.lookup("grdStu");
        grid.selectRows([1]);
    """)
    
    time.sleep(2)
    
    # Get selected student name after selection
    name_after = driver.execute_script(JS_FIND_APP + """
        var grid = inst.lookup("grdStu");
        var selectedIndices = grid.getSelectedRowIndices();
        if (selectedIndices.length > 0) {
            var ds = inst.lookup("dsStu");
            return ds.getValue(selectedIndices[0], "stuFlnm");
        }
        return "None";
    """)
    print(f"Selected student after: {name_after}")
    
    # Check dsGicRecStu rows
    row_count = driver.execute_script(JS_FIND_APP + """
        var ds = inst.lookup("dsGicRecStu");
        return ds ? ds.getRowCount() : -1;
    """)
    print(f"dsGicRecStu row count for 김가을: {row_count}")

if __name__ == "__main__":
    main()
