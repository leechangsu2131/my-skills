#!/usr/bin/env python3
"""
NEIS 학기말 종합의견 자동 입력 스크립트.
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
    var inst = instances.find(ai => ai.app && ai.app.id.includes("scres10_m00"));
    if (!inst) return {error: "App instance scres10_m00 not found"};
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
                
    raise RuntimeError("Could not find any window or frame with the NEIS school report opinion CPR app active.")

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

def get_subjects_dropdown(driver):
    """Get subjects from UDC combobox."""
    dismiss_alerts(driver)
    raw_list = driver.execute_script(JS_FIND_APP + """
        var udc = inst.lookup("udcSbjt");
        if (!udc) return {error: "udcSbjt not found"};
        var emb = udc.getEmbeddedAppInstance();
        if (!emb) return {error: "Embedded app of udcSbjt not found"};
        var cmb = emb.lookup("cmbUdcAuth");
        if (!cmb) return {error: "cmbUdcAuth not found"};
        
        var items = cmb.getItems();
        return items.map(function(it) {
            return {
                label: it.label,
                value: it.value
            };
        });
    """)
    if isinstance(raw_list, dict) and "error" in raw_list:
        return raw_list
        
    decoded = []
    for item in raw_list:
        decoded.append({
            "label": decode_cpr_str(item["label"]),
            "value": decode_cpr_str(item["value"])
        })
    return decoded

def switch_subject(driver, value, subject_name):
    """Switch NEIS to target subject."""
    dismiss_alerts(driver)
    
    # Revert any unsaved changes in dsMain to prevent UI blocking
    driver.execute_script(JS_FIND_APP + """
        var ds = inst.lookup("dsMain");
        if (ds && ds.isModified && ds.isModified()) {
            ds.revert();
        }
    """)
    
    res = driver.execute_script(JS_FIND_APP + f"""
        var udc = inst.lookup("udcSbjt");
        var emb = udc.getEmbeddedAppInstance();
        var cmb = emb.lookup("cmbUdcAuth");
        if (!cmb) return {{error: "cmbUdcAuth not found"}};
        cmb.selectItemByValue("{value}", true); // Trigger change event
        return {{ok: true, text: cmb.getSelectionFirst() ? cmb.getSelectionFirst().label : "none"}};
    """)
    
    if isinstance(res, dict) and "error" in res:
        print(f"  [switch] Error: {res['error']}")
        return False
        
    print(f"  [switch] Selected value for '{subject_name}'")
    time.sleep(3)
    return True

def click_search(driver):
    """Click query button."""
    dismiss_alerts(driver)
    res = driver.execute_script(JS_FIND_APP + """
        var btn = inst.lookup("btnSearch");
        if (!btn) return {error: "btnSearch not found"};
        btn.click();
        return {ok: true};
    """)
    if isinstance(res, dict) and "error" in res:
        print(f"  [search] Error: {res['error']}")
        return False
    time.sleep(3)
    return True

def fill_comments_for_subject(driver, subject_name, revisions_map):
    """Iterate dsMain students and fill their general opinions for the current subject."""
    dismiss_alerts(driver)
    
    # Check what students are in the current grid
    grid_students = driver.execute_script(JS_FIND_APP + """
        var ds = inst.lookup("dsMain");
        if (!ds) return {error: "dsMain not found"};
        var list = [];
        for (var i = 0; i < ds.getRowCount(); i++) {
            list.push({
                index: i,
                name: ds.getValue(i, "stdntNm") || ds.getValue(i, "stuFlnm")
            });
        }
        return list;
    """)
    
    if isinstance(grid_students, dict) and "error" in grid_students:
        return grid_students
        
    modified_count = 0
    updates_detail = []
    
    for item in grid_students:
        raw_name = item["name"]
        student_name = decode_cpr_str(raw_name)
        row_idx = item["index"]
        
        # Check if we have comment revisions for this student and subject
        student_revisions = revisions_map.get(student_name, {})
        target_comment = student_revisions.get(subject_name)
        
        if not target_comment:
            continue
            
        # Get current comment in grid
        current_comment = driver.execute_script(JS_FIND_APP + f"""
            var ds = inst.lookup("dsMain");
            return ds.getValue({row_idx}, "gnrlzOpiCn") || "";
        """)
        current_comment = decode_cpr_str(current_comment)
        
        if current_comment.strip() != target_comment.strip():
            # Update comment value programmatically in dataset
            js_target = json.dumps(target_comment, ensure_ascii=False)
            driver.execute_script(JS_FIND_APP + f"""
                var ds = inst.lookup("dsMain");
                ds.setValue({row_idx}, "gnrlzOpiCn", {js_target});
            """)
            modified_count += 1
            updates_detail.append(f"{student_name}: updated comment")
            
    if modified_count > 0:
        driver.execute_script(JS_FIND_APP + """
            var grid = inst.lookup("grdMain");
            if (grid) grid.redraw();
        """)
        
    return {
        "modified": modified_count > 0,
        "count": modified_count,
        "details": updates_detail
    }

def click_save(driver):
    """Click save and dismiss confirm/alert dialogs in parallel."""
    driver.execute_script(JS_FIND_APP + """
        var btn = inst.lookup("btnSave");
        if (btn) btn.click();
        return true;
    """)
    time.sleep(3)
    dismiss_alerts(driver)
    
    # 1. Click Confirm/확인 on all active/stale 'app/cmn/confirm' or 'app/cmn/alert' dialogs
    driver.execute_script("""
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var confirmApps = instances.filter(ai => ai && ai.app && (ai.app.id === "app/cmn/confirm" || ai.app.id === "app/cmn/alert"));
        confirmApps.forEach(function(confirmApp) {
            try {
                var container = confirmApp.getContainer();
                if (container) {
                    var clicked = false;
                    function findAndClick(ctrl) {
                        if (!ctrl || clicked) return;
                        var val = ctrl.value || ctrl.text || "";
                        var id = ctrl.id || "";
                        if (id === "btnOk" || id === "btnConfirm" || val === "확인" || val === "예" || val === "OK") {
                            if (typeof ctrl.click === 'function') {
                                try {
                                    ctrl.click();
                                    clicked = true;
                                } catch(e) {}
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
            } catch(e) {}
        });
    """)
    time.sleep(3)
    dismiss_alerts(driver)
    
    # 2. Click Confirm/확인 on the subsequent alert popup (if any)
    driver.execute_script("""
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var confirmApps = instances.filter(ai => ai && ai.app && (ai.app.id === "app/cmn/confirm" || ai.app.id === "app/cmn/alert"));
        confirmApps.forEach(function(confirmApp) {
            try {
                var container = confirmApp.getContainer();
                if (container) {
                    var clicked = false;
                    function findAndClick(ctrl) {
                        if (!ctrl || clicked) return;
                        var val = ctrl.value || ctrl.text || "";
                        var id = ctrl.id || "";
                        if (id === "btnOk" || id === "btnConfirm" || val === "확인" || val === "예" || val === "OK") {
                            if (typeof ctrl.click === 'function') {
                                try {
                                    ctrl.click();
                                    clicked = true;
                                } catch(e) {}
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
            } catch(e) {}
        });
    """)
    time.sleep(1)
    dismiss_alerts(driver)

def verify_saved(driver):
    """Check if dsMain modification state is cleared."""
    dismiss_alerts(driver)
    return driver.execute_script(JS_FIND_APP + """
        var ds = inst.lookup("dsMain");
        return ds ? !ds.isModified() : false;
    """)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", default="scratch/comment-revisions.json")
    parser.add_argument("--port", type=int, default=9222)
    parser.add_argument("--dry-run", action="store_true", help="Fill grid but do not save")
    parser.add_argument("--apply", action="store_true", help="Actually save to NEIS")
    parser.add_argument("--subjects", nargs="+", default=["국어", "수학", "사회", "도덕", "음악", "미술"], help="Subjects to process")
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
    
    # Locate active app context
    try:
        target_handle, target_frame = find_active_window_and_frame(driver)
        setup_target_context(driver, target_handle, target_frame)
    except Exception as e:
        print(f"Error finding active app: {e}")
        return

    # Get subjects dropdown list
    subjects = get_subjects_dropdown(driver)
    if isinstance(subjects, dict) and "error" in subjects:
        print(f"Error getting subjects: {subjects['error']}")
        return
        
    print(f"[subjects] Found {len(subjects)} subjects in dropdown.")
    
    # We want to process these subjects in order if they are in the dropdown
    target_subjects = args.subjects
    
    results = []
    
    for subject_name in target_subjects:
        # Find matching osuCd in subjects
        osu_cd = None
        for s in subjects:
            if s["label"] == subject_name:
                osu_cd = s["value"]
                break
                
        if not osu_cd:
            print(f"\n[Skip] Subject '{subject_name}' not found in NEIS. Skipping.")
            continue
            
        print(f"\n[Subject] Processing subject: {subject_name}")
        
        # 1. Switch subject
        if not switch_subject(driver, osu_cd, subject_name):
            print(f"  [Error] Failed to switch to {subject_name}")
            results.append({"subject": subject_name, "status": "Failed switch", "count": 0})
            continue
            
        # 2. Click Search
        if not click_search(driver):
            print(f"  [Error] Failed to search for {subject_name}")
            results.append({"subject": subject_name, "status": "Failed search", "count": 0})
            continue
            
        # 3. Fill comments
        fill_res = fill_comments_for_subject(driver, subject_name, revisions_map)
        if "error" in fill_res:
            print(f"  [Error] Error filling comments: {fill_res['error']}")
            results.append({"subject": subject_name, "status": "Error", "count": 0})
            continue
            
        modified = fill_res.get("modified")
        count = fill_res.get("count", 0)
        details = fill_res.get("details", [])
        
        print(f"  Modifications: {count} students updated. Details: {details}")
        
        # 4. Save if needed
        if modified and args.apply:
            print("  [Save] Saving...")
            click_save(driver)
            
            print("  Waiting 7 seconds for transaction to complete...")
            time.sleep(7)
            
            if verify_saved(driver):
                print("  [OK] Saved successfully!")
                results.append({"subject": subject_name, "status": "Saved", "count": count})
            else:
                print("  [Warning] Save unverified - grid might still be modified")
                # Revert
                driver.execute_script(JS_FIND_APP + "var ds = inst.lookup('dsMain'); if(ds) ds.revert();")
                results.append({"subject": subject_name, "status": "Unverified", "count": count})
        elif modified and args.dry_run:
            print("  [DRY-RUN] Changes made in browser grid, but not saved.")
            results.append({"subject": subject_name, "status": "Dry-run filled", "count": count})
            time.sleep(1.5)
        else:
            print("  [Info] No changes needed (already up-to-date or no revisions).")
            results.append({"subject": subject_name, "status": "No change", "count": 0})

    print(f"\n============================================================")
    print(f"Summary")
    print(f"============================================================")
    for entry in results:
        status_word = "[V]" if entry["status"] in ["Saved", "Dry-run filled"] else "[Info]" if entry["status"] == "No change" else "[X]"
        print(f"  {status_word} {entry['subject']}: {entry['status']} (updated count={entry['count']})")

if __name__ == "__main__":
    main()
