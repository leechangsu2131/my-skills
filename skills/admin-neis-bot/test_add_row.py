import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

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
    
    # Select index 1 (김가을)
    print("Selecting index 1 (김가을)...")
    driver.execute_script(JS_FIND_APP + """
        var grid = inst.lookup("grdStu");
        grid.selectRows([1]);
    """)
    
    time.sleep(2)
    
    # Check row count before adding
    row_count_before = driver.execute_script(JS_FIND_APP + """
        var ds = inst.lookup("dsGicRecStu");
        return ds ? ds.getRowCount() : -1;
    """)
    print(f"dsGicRecStu row count before: {row_count_before}")
    
    # Click btnAdd
    print("Clicking btnAdd...")
    driver.execute_script(JS_FIND_APP + """
        var btnAdd = inst.lookup("btnAdd");
        if (btnAdd) {
            btnAdd.click();
            return "Clicked btnAdd";
        }
        return "btnAdd not found";
    """)
    
    time.sleep(1)
    
    # Check row count after adding
    row_count_after = driver.execute_script(JS_FIND_APP + """
        var ds = inst.lookup("dsGicRecStu");
        return ds ? ds.getRowCount() : -1;
    """)
    print(f"dsGicRecStu row count after: {row_count_after}")
    
    if row_count_after > row_count_before:
        # Populate the added row (usually at index 0 or index row_count_after - 1)
        # Let's find which row is added. In eXBuilder6, inserting/adding a row can place it at index 0 or at the end.
        # Let's check which row has state INSERTED.
        new_row_idx = driver.execute_script(JS_FIND_APP + """
            var ds = inst.lookup("dsGicRecStu");
            for (var i = 0; i < ds.getRowCount(); i++) {
                var state = ds.getRowState(i);
                // cpr.data.RowState.INSERTED is 2
                if (state === 2 || state === "inserted" || ds.getRow(i).getRowState() === 2) {
                    return i;
                }
            }
            // fallback to last row
            return ds.getRowCount() - 1;
        """)
        print(f"New row index: {new_row_idx}")
        
        # Write test data
        driver.execute_script(JS_FIND_APP + f"""
            var ds = inst.lookup("dsGicRecStu");
            ds.setValue({new_row_idx}, "ghvrDevEnfcYmd", "20260316");
            ds.setValue({new_row_idx}, "ghvrDevCn", "자동화 테스트용 테스트 관찰 내용입니다.");
            
            var grid = inst.lookup("grdGicRecStu");
            if (grid) grid.redraw();
        """)
        print("Test data populated in grid.")
        
        time.sleep(2)
        
        # Revert changes to keep grid clean
        driver.execute_script(JS_FIND_APP + """
            var ds = inst.lookup("dsGicRecStu");
            if (ds) ds.revert();
            var grid = inst.lookup("grdGicRecStu");
            if (grid) grid.redraw();
        """)
        print("Changes reverted.")
    else:
        print("Failed to add row.")

if __name__ == "__main__":
    main()
