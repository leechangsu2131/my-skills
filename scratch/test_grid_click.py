import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

def main():
    o = Options()
    o.add_experimental_option("debuggerAddress", "localhost:9222")
    driver = webdriver.Chrome(options=o)
    
    # Locate the active NEIS window and frame
    # We will search for 'els_scres20_m00'
    driver.switch_to.default_content()
    
    # Check frames
    found_frame = None
    frames = driver.find_elements(By.TAG_NAME, "iframe")
    for frame in frames:
        fid = frame.get_attribute("id") or frame.get_attribute("name")
        driver.switch_to.default_content()
        driver.switch_to.frame(frame)
        try:
            has_cpr = driver.execute_script("return typeof cpr !== 'undefined';")
            if has_cpr:
                app_exists = driver.execute_script("""
                    var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
                    return instances.some(ai => ai.app && ai.app.id.includes("scres20_m00"));
                """)
                if app_exists:
                    found_frame = frame
                    break
        except Exception:
            pass
            
    if found_frame:
        print("Found app in frame:", found_frame.get_attribute("id"))
    else:
        print("Could not find frame, staying in default content")
        driver.switch_to.default_content()

    # Let's inspect the DOM elements inside the grid
    # We will execute a script to click the cell corresponding to row 1 (second row)
    # A grid has rows with class 'cl-grid-row' or similar, or we can use selector
    # Let's find elements that represent rows or cells
    # We can execute a script to click the cell corresponding to row 1 (second row)
    click_success = driver.execute_script("""
        const platform = window.cpr && cpr.core.Platform && cpr.core.Platform.INSTANCE;
        const app = platform.getAllRunningAppInstances().find(ai => ai.app && ai.app.id.includes('scres20_m00'));
        const grid = app.lookup('grdStdnt');
        if (!grid) return {error: "Grid not found"};
        
        // Let's click the second student (row index 1)
        // CPR Grid API provides grid.clickCell(rowIndex, colIndex) or grid.selectRows(rowIndex, true)
        // Let's try triggering selection-change event manually or clickCell
        try {
            grid.clickCell(1, 0); // Click row 1, col 0
            return {ok: true, method: "clickCell"};
        } catch(e) {
            try {
                // If clickCell is not supported, let's dispatch click event on the cell element
                const cellEl = grid.getCellElement(1, 0);
                if (cellEl) {
                    cellEl.click();
                    return {ok: true, method: "DOM click"};
                }
            } catch(e2) {
                return {error: e.toString() + " | " + e2.toString()};
            }
        }
    """)
    print("Click attempt result:", click_success)
    
    time.sleep(2)
    
    # Verify if detail changed
    verify = driver.execute_script("""
        const platform = window.cpr && cpr.core.Platform && cpr.core.Platform.INSTANCE;
        const app = platform.getAllRunningAppInstances().find(ai => ai.app && ai.app.id.includes('scres20_m00'));
        const ds = app.lookup('dsGnrlzOpinListByYear');
        return {
            rowCount: ds.getRowCount(), 
            studentInDetail: ds.getRowCount() > 0 ? ds.getValue(0, 'stuFlnm') : 'none',
            currentStudentInGrid: app.lookup('grdStdnt').getSelectedRowIndices()
        };
    """)
    print("Verification result:", verify)

if __name__ == "__main__":
    main()
