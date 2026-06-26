import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))
from neis_behavioral_opinion_writer import connect_cdp, find_active_window_and_frame, setup_target_context, JS_FIND_APP

def main():
    driver = connect_cdp()
    h, f = find_active_window_and_frame(driver)
    setup_target_context(driver, h, f)
    driver.execute_script(JS_FIND_APP + """
        var ds = inst.lookup("dsScrgRec");
        if (ds && ds.isModified && ds.isModified()) {
            console.log("Reverting dsScrgRec changes");
            ds.revert();
        }
        var btn = inst.lookup("btnSearch");
        if (btn) {
            console.log("Clicking btnSearch");
            btn.click();
        }
    """)
    print("[success] Reverted changes and clicked search button.")

if __name__ == "__main__":
    main()
