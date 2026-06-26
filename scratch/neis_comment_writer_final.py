#!/usr/bin/env python3
"""
NEIS 교과학습발달상황 평어 자동 입력 최종 스크립트.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

REMOTE_PORT = 9222

JS_FIND_APP = """
    var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var inst = instances.find(ai => ai.app && ai.app.id.includes("scres20_m00"));
    if (!inst) return {error: "App instance scres20_m00 not found"};
"""

def decode_cpr_str(s: str) -> str:
    if not s:
        return ""
    try:
        return s.encode('latin1').decode('euc-kr')
    except Exception:
        return s

def connect_cdp(port: int = REMOTE_PORT):
    opts = Options()
    opts.add_experimental_option("debuggerAddress", f"localhost:{port}")
    driver = webdriver.Chrome(options=opts)
    print(f"[connect] Connected to Chrome: {driver.title}")
    return driver

def dismiss_alerts(driver):
    """Dismiss browser alerts."""
    from selenium.common.exceptions import NoAlertPresentException
    try:
        alert = driver.switch_to.alert
        text = alert.text
        print(f"  [alert] Dismissed alert: '{text}'")
        alert.accept()
        time.sleep(1)
        dismiss_alerts(driver)
    except NoAlertPresentException:
        pass

def find_active_window_and_frame(driver):
    """Scan windows and frames to locate where the NEIS CPR app is running."""
    handles = driver.window_handles
    for handle in handles:
        driver.switch_to.window(handle)
        
        # 1. Check main frame
        driver.switch_to.default_content()
        try:
            has_cpr = driver.execute_script("return typeof cpr !== 'undefined';")
            if has_cpr:
                app_info = driver.execute_script(JS_FIND_APP + "return {ok: true, appId: inst.app.id};")
                if "ok" in app_info:
                    print(f"[location] Found NEIS app '{app_info['appId']}' in main frame of window '{driver.title}'")
                    return handle, None
        except Exception:
            pass

        # 2. Check iframes
        frames = driver.find_elements(By.TAG_NAME, "iframe")
        for i, frame in enumerate(frames):
            fid = frame.get_attribute("id") or frame.get_attribute("name") or f"index_{i}"
            try:
                driver.switch_to.default_content()
                driver.switch_to.frame(frame)
                has_cpr = driver.execute_script("return typeof cpr !== 'undefined';")
                if has_cpr:
                    app_info = driver.execute_script(JS_FIND_APP + "return {ok: true, appId: inst.app.id};")
                    if "ok" in app_info:
                        print(f"[location] Found NEIS app '{app_info['appId']}' in frame '{fid}' of window '{driver.title}'")
                        return handle, fid
            except Exception:
                pass
                
    raise RuntimeError("Could not find any window or frame with the NEIS evaluation CPR app active.")

def setup_target_context(driver, target_handle, target_frame):
    """Switch to the window and frame where the app is located."""
    driver.switch_to.window(target_handle)
    driver.switch_to.default_content()
    if target_frame:
        frames = driver.find_elements(By.TAG_NAME, "iframe")
        for frame in frames:
            if frame.get_attribute("id") == target_frame or frame.get_attribute("name") == target_frame:
                driver.switch_to.frame(frame)
                return
        raise RuntimeError(f"Frame {target_frame} not found")

def get_student_list(driver):
    """Get the student list from dsStdnt."""
    dismiss_alerts(driver)
    raw_list = driver.execute_script(JS_FIND_APP + """
        var ds = inst.lookup("dsStdnt");
        if (!ds) return {error: "dsStdnt not found"};
        var list = [];
        for (var i = 0; i < ds.getRowCount(); i++) {
            list.push({
                index: i,
                name: ds.getValue(i, "stdntNm") || ds.getValue(i, "stuFlnm"),
                stuInvlNo: ds.getValue(i, "stuInvlNo")
            });
        }
        return list;
    """)
    if isinstance(raw_list, dict) and "error" in raw_list:
        return raw_list
        
    # Decode student names
    decoded = []
    for item in raw_list:
        decoded.append({
            "index": item["index"],
            "name": decode_cpr_str(item["name"]),
            "stuInvlNo": item["stuInvlNo"]
        })
    return decoded

def click_student_row(driver, student_name):
    """Find and click the student row in the grid using general XPath and JS click."""
    dismiss_alerts(driver)
    xpath = f"//*[contains(text(), '{student_name}')]"
    try:
        elements = driver.find_elements(By.XPATH, xpath)
        if not elements:
            print(f"  [click] No elements found for student '{student_name}'. Attempting grid scroll fallback...")
            driver.execute_script("""
                var allGrids = document.querySelectorAll('.cl-grid');
                for (var i = 0; i < allGrids.length; i++) {
                    var txt = allGrids[i].innerText || "";
                    if (txt.includes("순번") || txt.includes("성명")) {
                        allGrids[i].scrollTop = 0;
                        var children = allGrids[i].querySelectorAll('*');
                        for (var j = 0; j < children.length; j++) {
                            if (children[j].scrollHeight > children[j].clientHeight) {
                                children[j].scrollTop = 0;
                            }
                        }
                    }
                }
            """)
            time.sleep(1)
            elements = driver.find_elements(By.XPATH, xpath)
            if not elements:
                print(f"  [click] Still no elements found for student '{student_name}' after scroll fallback.")
                return False
        
        # Scroll element into view and click using JS click to bypass interactivity checks
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elements[0])
        time.sleep(0.2)
        driver.execute_script("arguments[0].click();", elements[0])
        return True
    except Exception as e:
        print(f"  [click] Failed to click student '{student_name}': {e}")
        return False

def fill_comments_for_student(driver, student_name, revisions_map):
    """Fill subject comments for the selected student in dsGnrlzOpinListByYear."""
    student_revisions = revisions_map.get(student_name, {})
    if not student_revisions:
        return {"modified": False, "reason": "No revisions for this student"}
        
    js_map = json.dumps(student_revisions, ensure_ascii=False)
    
    return driver.execute_script(JS_FIND_APP + f"""
        var revs = {js_map};
        var ds = inst.lookup("dsGnrlzOpinListByYear");
        var grid = inst.lookup("grdCurrByRec");
        if (!ds || !grid) return {{error: "dsGnrlzOpinListByYear or grdCurrByRec not found"}};
        
        var modifiedCount = 0;
        var details = [];
        
        for (var i = 0; i < ds.getRowCount(); i++) {{
            var sbjtNm = ds.getValue(i, "sbjtNm");
            var currentVal = ds.getValue(i, "gnrlzOpiCn") || "";
            
            if (sbjtNm in revs) {{
                var targetVal = revs[sbjtNm];
                if (currentVal.trim() !== targetVal.trim()) {{
                    ds.setValue(i, "gnrlzOpiCn", targetVal);
                    modifiedCount++;
                    details.push(sbjtNm + ": updated");
                }} else {{
                    details.push(sbjtNm + ": already matches");
                }}
            }}
        }}
        
        if (modifiedCount > 0) {{
            grid.redraw();
        }}
        
        return {{
            modified: ds.isModified(),
            count: modifiedCount,
            details: details
        }};
    """)

def click_save(driver):
    """Click save and dismiss confirm/alert dialogs."""
    driver.execute_script(JS_FIND_APP + """
        var btn = inst.lookup("btnSave");
        if (btn) btn.click();
        return true;
    """)
    time.sleep(3)
    
    dismiss_alerts(driver)
    
    # 1. Click Confirm/확인 on 'app/cmn/confirm' or 'app/cmn/alert'
    driver.execute_script("""
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var confirmApp = instances.find(ai => ai.app && (ai.app.id === "app/cmn/confirm" || ai.app.id === "app/cmn/alert"));
        if (confirmApp) {
            var container = confirmApp.getContainer();
            if (container) {
                var clicked = false;
                function findAndClick(ctrl) {
                    if (!ctrl || clicked) return;
                    var val = ctrl.value || ctrl.text || "";
                    var id = ctrl.id || "";
                    if (id === "btnOk" || id === "btnConfirm" || val === "확인" || val === "예" || val === "OK") {
                        if (typeof ctrl.click === 'function') {
                            ctrl.click();
                            clicked = true;
                        }
                    }
                    if (typeof ctrl.getChildren === 'function') {
                        var children = ctrl.getChildren();
                        for (var j = 0; j < children.length; j++) {
                            findAndClick(children[j]);
                        }
                    }
                }
                findAndClick(container);
            }
        }
    """)
    time.sleep(3)
    
    dismiss_alerts(driver)
    
    # 2. Click Confirm/확인 on the subsequent alert popup (if any)
    driver.execute_script("""
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var confirmApp = instances.find(ai => ai.app && (ai.app.id === "app/cmn/confirm" || ai.app.id === "app/cmn/alert"));
        if (confirmApp) {
            var container = confirmApp.getContainer();
            if (container) {
                var clicked = false;
                function findAndClick(ctrl) {
                    if (!ctrl || clicked) return;
                    var val = ctrl.value || ctrl.text || "";
                    var id = ctrl.id || "";
                    if (id === "btnOk" || id === "btnConfirm" || val === "확인" || val === "예" || val === "OK") {
                        if (typeof ctrl.click === 'function') {
                            ctrl.click();
                            clicked = true;
                        }
                    }
                    if (typeof ctrl.getChildren === 'function') {
                        var children = ctrl.getChildren();
                        for (var j = 0; j < children.length; j++) {
                            findAndClick(children[j]);
                        }
                    }
                }
                findAndClick(container);
            }
        }
    """)
    time.sleep(1)
    dismiss_alerts(driver)

def verify_saved(driver):
    """Check if modification state is cleared."""
    dismiss_alerts(driver)
    return driver.execute_script(JS_FIND_APP + """
        var ds = inst.lookup("dsGnrlzOpinListByYear");
        return ds ? !ds.isModified() : false;
    """)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", default="scratch/comment-revisions.json")
    parser.add_argument("--port", type=int, default=9222)
    parser.add_argument("--dry-run", action="store_true", help="Fill grid but do not save")
    parser.add_argument("--apply", action="store_true", help="Actually save to NEIS")
    args = parser.parse_args()
    
    if not args.dry_run and not args.apply:
        print("Please specify either --dry-run or --apply")
        return

    # Load parsed comments
    records_path = Path(args.records)
    if not records_path.exists():
        print(f"Error: Records file not found at {records_path}.")
        return
        
    records = json.loads(records_path.read_text(encoding="utf-8"))
    print(f"[init] Loaded {len(records)} comment records.")
    
    # Restructure into {student_name: {subject_name: comment}}
    revisions_map = {}
    for r in records:
        student = r["student"]
        subject = r["subject"]
        comment = r["comment"]
        if student not in revisions_map:
            revisions_map[student] = {}
        revisions_map[student][subject] = comment
        
    driver = connect_cdp(args.port)
    
    # Context alignment
    try:
        target_handle, target_frame = find_active_window_and_frame(driver)
        setup_target_context(driver, target_handle, target_frame)
    except Exception as e:
        print(f"Error finding active app: {e}")
        return

    # Get students
    students = get_student_list(driver)
    if isinstance(students, dict) and "error" in students:
        print(f"Error reading students: {students['error']}. Are you on the right screen?")
        return
        
    print(f"[students] Found {len(students)} students in the grid.")
    
    results = []
    
    for idx, std in enumerate(students, 1):
        name = std["name"]
        print(f"\n[{idx}/{len(students)}] Processing student: {name}")
        
        # Click row in left grid
        if not click_student_row(driver, name):
            print(f"  [Error] Failed to select student {name}. Skipping.")
            results.append({"name": name, "status": "Failed select", "count": 0})
            continue
            
        # Wait for detail dataset to load
        time.sleep(2)
        
        # Fill comments
        fill_res = fill_comments_for_student(driver, name, revisions_map)
        if "error" in fill_res:
            print(f"  [Error] Error filling comments: {fill_res['error']}")
            results.append({"name": name, "status": "Error", "count": 0})
            continue
            
        modified = fill_res.get("modified")
        count = fill_res.get("count", 0)
        details = fill_res.get("details", [])
        
        print(f"  Modifications: {count} subjects updated. Details: {details}")
        
        if modified and args.apply:
            print("  [Save] Saving...")
            click_save(driver)
            
            print("  Waiting 7 seconds for transaction to complete...")
            time.sleep(7)
            
            if verify_saved(driver):
                print("  [OK] Saved successfully!")
                results.append({"name": name, "status": "Saved", "count": count})
            else:
                print("  [Warning] Save unverified - grid might still be modified")
                # Revert
                driver.execute_script(JS_FIND_APP + "var ds = inst.lookup('dsGnrlzOpinListByYear'); if(ds) ds.revert();")
                results.append({"name": name, "status": "Unverified", "count": count})
        elif modified and args.dry_run:
            print("  [DRY-RUN] Changes made in browser grid, but not saved.")
            results.append({"name": name, "status": "Dry-run filled", "count": count})
            time.sleep(1.5)
        else:
            print("  [Info] No changes needed (already up-to-date or no revisions).")
            results.append({"name": name, "status": "No change", "count": 0})

    print(f"\n============================================================")
    print(f"Summary")
    print(f"============================================================")
    for entry in results:
        status_word = "[V]" if entry["status"] in ["Saved", "Dry-run filled"] else "[Info]" if entry["status"] == "No change" else "[X]"
        print(f"  {status_word} {entry['name']}: {entry['status']} (updated count={entry['count']})")

if __name__ == "__main__":
    main()
