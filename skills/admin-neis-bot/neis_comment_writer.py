#!/usr/bin/env python3
"""
NEIS 교과학습발달상황 평어 자동 입력 스크립트.
"""

from __future__ import annotations

import argparse
import json
import time
import sys
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

REMOTE_PORT = 9222

# Find the CPR app instance. We will dynamically search for the correct evaluation app.
# By default, it's edu/sw/els/scr/es/els_scres00_m00 or similar.
# We will search all instances and look for the one containing dsMain and udcSbjt.
JS_FIND_APP_TEMPLATE = """
    var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var inst = null;
    for (var i = 0; i < instances.length; i++) {
        var ai = instances[i];
        if (ai.app && (ai.app.id.indexOf("edu/sw/els/scr/") >= 0 || ai.lookup("grdMain"))) {
            inst = ai;
            break;
        }
    }
    if (!inst && instances.length > 0) {
        // Fallback to the main active sub-app
        inst = instances.find(ai => ai.app && ai.app.id !== "app/com/main/Index" && ai.app.id !== "udc/com/loadmask");
    }
    if (!inst) return {error: "No active NEIS evaluation app instance found"};
"""

def connect_cdp(port: int = REMOTE_PORT):
    opts = Options()
    opts.add_experimental_option("debuggerAddress", f"localhost:{port}")
    driver = webdriver.Chrome(options=opts)
    print(f"[connect] Connected to: {driver.title}")
    dismiss_alerts(driver)
    return driver

def dismiss_alerts(driver):
    """Dismiss any unexpected browser system alerts (like session expiration or warnings)."""
    from selenium.common.exceptions import NoAlertPresentException
    try:
        alert = driver.switch_to.alert
        text = alert.text
        print(f"  [alert] Dismissing browser system alert: '{text}'")
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
                app_info = driver.execute_script(JS_FIND_APP_TEMPLATE + "return {ok: true, appId: inst.app.id};")
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
                    app_info = driver.execute_script(JS_FIND_APP_TEMPLATE + "return {ok: true, appId: inst.app.id};")
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

def get_cpr_app_id(driver):
    return driver.execute_script(JS_FIND_APP_TEMPLATE + "return inst.app.id;")

def get_all_subjects(driver):
    """Get all available subjects from the udcSbjt control."""
    dismiss_alerts(driver)
    return driver.execute_script(JS_FIND_APP_TEMPLATE + """
        var udc = inst.lookup("udcSbjt");
        if (!udc) return {error: "udcSbjt not found"};
        var embApp = udc.getEmbeddedAppInstance();
        var dsAuth = embApp.lookup("dsAuth");
        if (!dsAuth) return {error: "dsAuth not found"};
        
        var subjects = [];
        for (var i = 0; i < dsAuth.getRowCount(); i++) {
            subjects.push({
                index: i,
                nm: dsAuth.getValue(i, "nm"),
                cd: dsAuth.getValue(i, "cd"),
                osuCd: dsAuth.getValue(i, "osuCd")
            });
        }
        return {current: udc.getText(), subjects: subjects};
    """)

def switch_subject(driver, osu_cd, expected_name):
    """Switch subject using the internal cmbUdcAuth."""
    dismiss_alerts(driver)
    # Revert any unsaved changes in dsMain to prevent UI blocking
    driver.execute_script(JS_FIND_APP_TEMPLATE + """
        var ds = inst.lookup("dsMain");
        if (ds && ds.isModified && ds.isModified()) {
            ds.revert();
        }
    """)
    
    result = driver.execute_script(JS_FIND_APP_TEMPLATE + f"""
        var udc = inst.lookup("udcSbjt");
        if (!udc) return {{error: "udcSbjt not found"}};
        var embApp = udc.getEmbeddedAppInstance();
        var cmb = embApp.lookup("cmbUdcAuth");
        if (!cmb) return {{error: "cmbUdcAuth not found in udcSbjt"}};
        
        cmb.selectItemByValue("{osu_cd}", true); // Trigger change events
        return {{ok: true, selected: cmb.getSelectionFirst() ? cmb.getSelectionFirst().label : "none"}};
    """)
    
    if result.get("error"):
        print(f"  [switch] ERROR: {result['error']}")
        return False
    
    time.sleep(3)
    
    # Verify switch
    verify = driver.execute_script(JS_FIND_APP_TEMPLATE + """
        var udc = inst.lookup("udcSbjt");
        return {text: udc.getText(), value: udc.getValue()};
    """)
    
    print(f"  [switch] Verified Subject: text='{verify.get('text')}' value='{verify.get('value')}'")
    if verify.get("text") != expected_name:
        print(f"  [switch] WARNING: Expected '{expected_name}', got '{verify.get('text')}'")
        return False
    return True

def search_current_subject(driver):
    """Click the search button."""
    dismiss_alerts(driver)
    driver.execute_script(JS_FIND_APP_TEMPLATE + """
        var btn = inst.lookup("btnSearch");
        if (btn) btn.click();
        return true;
    """)
    time.sleep(3)

def detect_comment_column(driver):
    """Dynamically detect which column in dsMain holds the comment (평어) text."""
    return driver.execute_script(JS_FIND_APP_TEMPLATE + """
        var ds = inst.lookup("dsMain");
        if (!ds) return {error: "dsMain not found"};
        
        var cols = [];
        for (var i = 0; i < ds.getColumnCount(); i++) {
            var c = ds.getColumn(i);
            if (c) {
                cols.push(c.columnName || c.name || String(c));
            }
        }
        
        // Find columns containing 'Rpt', 'Cn', 'Evl', 'Ctr' or check samples
        var targetCol = null;
        var candidates = ["sbjtRptCn", "evlCtrCn", "sbjtEvlCn", "evlCn", "cmnt"];
        for (var k = 0; k < candidates.length; k++) {
            if (cols.indexOf(candidates[k]) >= 0) {
                targetCol = candidates[k];
                break;
            }
        }
        
        if (!targetCol) {
            // Check sample row values to find a long text field
            if (ds.getRowCount() > 0) {
                for (var j = 0; j < cols.length; j++) {
                    var val = ds.getValue(0, cols[j]);
                    if (val && typeof val === "string" && val.length > 5) {
                        targetCol = cols[j];
                        break;
                    }
                }
            }
        }
        
        return {cols: cols, detected: targetCol};
    """)

def get_grid_state(driver, comment_col):
    """Get current grid rows, student names, and existing comment values."""
    dismiss_alerts(driver)
    return driver.execute_script(JS_FIND_APP_TEMPLATE + f"""
        var ds = inst.lookup("dsMain");
        if (!ds) return {{error: "dsMain not found"}};
        
        var rows = [];
        for (var i = 0; i < ds.getRowCount(); i++) {{
            rows.push({{
                i: i,
                name: ds.getValue(i, "stuFlnm") || ds.getValue(i, "stdNm") || ds.getValue(i, "stuNm") || "",
                comment: ds.getValue(i, "{comment_col}") || ""
            }});
        }}
        return {{modified: ds.isModified(), total: ds.getRowCount(), rows: rows}};
    """)

def fill_comments(driver, records, comment_col):
    """Fill the grid dataset with comments."""
    comment_map = {r["student"]: r["comment"] for r in records}
    
    js_comment_map = json.dumps(comment_map, ensure_ascii=False)
    
    return driver.execute_script(JS_FIND_APP_TEMPLATE + f"""
        var commentMap = {js_comment_map};
        var commentCol = "{comment_col}";
        
        var ds = inst.lookup("dsMain");
        var grid = inst.lookup("grdMain");
        if (!ds || !grid) return {{error: "Controls not found"}};
        
        var filled = 0;
        var skipped = [];
        var unmatched = [];
        
        for (var i = 0; i < ds.getRowCount(); i++) {{
            var stuName = ds.getValue(i, "stuFlnm") || ds.getValue(i, "stdNm") || ds.getValue(i, "stuNm") || "";
            var baseName = stuName.replace(/\\(.+\\)/, "").trim();
            
            if (!(baseName in commentMap)) {{
                unmatched.push(baseName);
                continue;
            }}
            
            var targetComment = commentMap[baseName];
            var currentComment = ds.getValue(i, commentCol) || "";
            
            if (currentComment.trim() === targetComment.trim()) {{
                skipped.push({{name: baseName, reason: "Already matches target comment"}});
                continue;
            }}
            
            ds.setValue(i, commentCol, targetComment);
            filled++;
        }}
        
        grid.redraw();
        
        return {{
            ok: true,
            filled: filled,
            skipped: skipped,
            unmatched: unmatched,
            modified: ds.isModified(),
            total: ds.getRowCount()
        }};
    """)

def save_grid(driver):
    """Click save and handle confirmation modals."""
    driver.execute_script(JS_FIND_APP_TEMPLATE + """
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
    return driver.execute_script(JS_FIND_APP_TEMPLATE + """
        var ds = inst.lookup("dsMain");
        return ds ? !ds.isModified() : false;
    """)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", default="scratch/comment-revisions.json")
    parser.add_argument("--port", type=int, default=9222)
    parser.add_argument("--subjects", nargs="*", help="Specific subjects to process (e.g., 음악 미술 국어)")
    parser.add_argument("--dry-run", action="store_true", help="Fill grid but do not save")
    parser.add_argument("--apply", action="store_true", help="Actually save to NEIS")
    args = parser.parse_args()
    
    if not args.dry_run and not args.apply:
        print("Please specify either --dry-run or --apply")
        return

    # Load parsed comments
    records_path = Path(args.records)
    if not records_path.exists():
        print(f"Error: Records file not found at {records_path}. Run parser first.")
        return
        
    all_records = json.loads(records_path.read_text(encoding="utf-8"))
    print(f"[init] Loaded {len(all_records)} comment revision records.")
    
    driver = connect_cdp(args.port)
    
    # Locate CPR app frame
    try:
        target_handle, target_frame = find_active_window_and_frame(driver)
        setup_target_context(driver, target_handle, target_frame)
    except Exception as e:
        print(f"Error: {e}")
        print("Please ensure you are logged into NEIS and have opened the evaluation screen.")
        return

    app_id = get_cpr_app_id(driver)
    print(f"[app] Active App: {app_id}")
    
    # Get subjects
    subj_info = get_all_subjects(driver)
    if "error" in subj_info:
        print(f"Error reading subjects: {subj_info['error']}")
        return
        
    print(f"\n[subjects] Current Selected Subject: {subj_info['current']}")
    print(f"[subjects] Available Subjects in dropdown:")
    for s in subj_info["subjects"]:
        print(f"  - {s['nm']} (cd={s['cd']}, osuCd={s['osuCd']})")
        
    subject_map = {s["nm"]: s for s in subj_info["subjects"]}
    
    # Target subjects to process
    target_subjects = args.subjects if args.subjects else ["국어", "수학", "사회", "도덕", "음악", "미술"]
    
    results_log = []
    
    for subject_name in target_subjects:
        # Match subject name in map
        subj_entry = subject_map.get(subject_name)
        if not subj_entry:
            # Try partial matching
            for k, v in subject_map.items():
                if subject_name in k or k in subject_name:
                    subj_entry = v
                    subject_name = k
                    break
                    
        if not subj_entry:
            print(f"\nSubject '{subject_name}' not found in NEIS dropdown. Skipping.")
            continue
            
        print(f"\n============================================================")
        print(f"📚 Subject: {subject_name}")
        print(f"============================================================")
        
        # Filter comments for this subject
        subj_records = [r for r in all_records if r["subject"] == subject_name]
        if not subj_records:
            print(f"  No comment records to modify for {subject_name}.")
            continue
            
        print(f"  Revisions to write: {len(subj_records)}")
        
        # Switch subject
        print(f"  Switching to {subject_name}...")
        if not switch_subject(driver, subj_entry["cd"], subject_name):
            print(f"  ❌ Failed to switch to {subject_name}")
            continue
            
        # Click search
        print(f"  Searching...")
        search_current_subject(driver)
        
        # Detect comment column
        col_info = detect_comment_column(driver)
        if "error" in col_info:
            print(f"  ❌ Error detecting dataset: {col_info['error']}")
            continue
            
        comment_col = col_info.get("detected")
        if not comment_col:
            print(f"  ❌ Could not detect comment column in: {col_info.get('cols')}")
            continue
            
        print(f"  Detected comment column: '{comment_col}' out of {col_info.get('cols')}")
        
        # Check current state
        state = get_grid_state(driver, comment_col)
        print(f"  Current grid: {state.get('total')} rows. Modified: {state.get('modified')}")
        
        # Fill comments
        fill_res = fill_comments(driver, subj_records, comment_col)
        if "error" in fill_res:
            print(f"  ❌ Error filling comments: {fill_res['error']}")
            continue
            
        print(f"  Filled: {fill_res.get('filled')} rows. Skipped: {len(fill_res.get('skipped', []))}")
        if fill_res.get("unmatched"):
            print(f"  ⚠ Unmatched students: {fill_res.get('unmatched')}")
            
        if fill_res.get("modified") and args.apply:
            print("  💾 Saving...")
            save_grid(driver)
            
            print("  Waiting 7 seconds for transaction to complete...")
            time.sleep(7)
            
            if verify_saved(driver):
                print("  ✅ Saved successfully!")
                results_log.append({
                    "subject": subject_name,
                    "status": "Saved",
                    "filled": fill_res.get("filled")
                })
            else:
                print("  ⚠ Save unverified - grid might still be modified")
                driver.execute_script(JS_FIND_APP_TEMPLATE + "var ds = inst.lookup('dsMain'); if(ds) ds.revert();")
                results_log.append({
                    "subject": subject_name,
                    "status": "Unverified"
                })
        elif fill_res.get("modified") and args.dry_run:
            print("  [DRY-RUN] Changes made in browser grid, but not saved.")
            results_log.append({
                "subject": subject_name,
                "status": "Dry-run filled",
                "filled": fill_res.get("filled")
            })
            # Wait for user to inspect
            time.sleep(2)
        else:
            print("  ℹ No changes needed (already up-to-date).")
            results_log.append({
                "subject": subject_name,
                "status": "No change"
            })

    print(f"\n============================================================")
    print(f"📊 Summary")
    print(f"============================================================")
    for entry in results_log:
        icon = "✅" if entry["status"] in ["Saved", "Dry-run filled"] else "ℹ️" if entry["status"] == "No change" else "❌"
        print(f"  {icon} {entry['subject']}: {entry['status']} (filled={entry.get('filled', 0)})")

if __name__ == "__main__":
    main()
