#!/usr/bin/env python3
"""
NEIS 창체 및 진로활동 자동 입력 스크립트.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

REMOTE_PORT = 9222

JS_FIND_APP = """
    var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var inst = instances.find(ai => ai.app && ai.app.id.includes("els_sdlce06_m00"));
    if (!inst) return {error: "App instance els_sdlce06_m00 not found"};
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

        try:
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
        except Exception:
            pass
                
    raise RuntimeError("Could not find any window or frame with the NEIS 창체/진로활동 CPR app active.")

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

def parse_markdown_changche(filepath: Path) -> tuple[dict[str, str], dict[str, str]]:
    """Parse the markdown file and return two dictionaries: student -> opinion text."""
    content = filepath.read_text(encoding="utf-8")
    
    # Extract sections
    # section 1: 가. 자율·자치활동 및 동아리활동
    sec1_match = re.search(r"### 가\.\s*자율·자치활동 및 동아리활동\s*\n(.*?)(?=\n###|\n##|\n---)", content, re.DOTALL)
    sec1_text = sec1_match.group(1) if sec1_match else ""
    
    # section 2: 나. 진로활동
    sec2_match = re.search(r"### 나\.\s*진로활동\s*\n(.*?)(?=\n###|\n##|\n---)", content, re.DOTALL)
    sec2_text = sec2_match.group(1) if sec2_match else ""
    
    student_pattern = re.compile(r"\*\*(\d+)\.\s*([^\*]+)\*\*\s*\n([^\n]+)")
    
    # Parse section 1 (자율/동아리)
    sec1_map = {}
    for num, name, text in student_pattern.findall(sec1_text):
        name = name.strip()
        sec1_map[name] = text.strip()
        print(f"[parsed 자율/동아리] No.{num} {name}: {len(text.strip())} chars")
        
    # Parse section 2 (진로)
    sec2_map = {}
    for num, name, text in student_pattern.findall(sec2_text):
        name = name.strip()
        sec2_map[name] = text.strip()
        print(f"[parsed 진로] No.{num} {name}: {len(text.strip())} chars")
        
    return sec1_map, sec2_map

def fill_comments(driver, sec1_map: dict[str, str], sec2_map: dict[str, str]) -> dict[str, any]:
    """Iterate dsScrgRec students and fill opinions depending on activity code."""
    dismiss_alerts(driver)
    
    # Check what rows are in the current grid
    grid_rows = driver.execute_script(JS_FIND_APP + """
        var ds = inst.lookup("dsScrgRec");
        if (!ds) return {error: "dsScrgRec not found"};
        var list = [];
        for (var i = 0; i < ds.getRowCount(); i++) {
            list.push({
                index: i,
                name: ds.getValue(i, "stuFlnm") || ds.getValue(i, "stdntNm") || "",
                actScCd: ds.getValue(i, "actScCd") || "",
                actScNm: ds.getValue(i, "actScNm") || "",
                opinion: ds.getValue(i, "speclActSpablMteCn") || ""
            });
        }
        return list;
    """)
    
    if isinstance(grid_rows, dict) and "error" in grid_rows:
        return grid_rows
        
    modified_count = 0
    updates_detail = []
    
    for item in grid_rows:
        raw_name = item["name"]
        student_name = decode_cpr_str(raw_name)
        # Strip any parenthesized suffix like (전입학)
        student_name = re.sub(r"\(.*?\)", "", student_name).strip()
        
        row_idx = item["index"]
        act_cd = item["actScCd"]
        act_nm = decode_cpr_str(item["actScNm"])
        current_opinion = decode_cpr_str(item["opinion"])
        
        target_opinion = None
        category = ""
        
        # Mapping rules
        if act_cd == "20":
            target_opinion = sec1_map.get(student_name)
            category = "자율/동아리"
        elif act_cd == "14":
            target_opinion = sec2_map.get(student_name)
            category = "진로"
            
        if not target_opinion:
            continue
            
        if current_opinion.strip() != target_opinion.strip():
            js_target = json.dumps(target_opinion, ensure_ascii=False)
            driver.execute_script(JS_FIND_APP + f"""
                var ds = inst.lookup("dsScrgRec");
                ds.setValue({row_idx}, "speclActSpablMteCn", {js_target});
            """)
            modified_count += 1
            updates_detail.append(f"{student_name} ({category}): updated")
            
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
    
    # Click Confirm/확인 on all active/stale 'app/cmn/confirm' or 'app/cmn/alert' dialogs
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

def verify_saved(driver):
    """Check if dsScrgRec modification state is cleared."""
    dismiss_alerts(driver)
    return driver.execute_script(JS_FIND_APP + """
        var ds = inst.lookup("dsScrgRec");
        return ds ? !ds.isModified() : false;
    """)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="skills/classmanage-evaluate-to-neis/data/2026_1학기_행동특성_창체v2.md")
    parser.add_argument("--port", type=int, default=9222)
    parser.add_argument("--dry-run", action="store_true", help="Fill grid but do not save")
    parser.add_argument("--apply", action="store_true", help="Actually save to NEIS")
    args = parser.parse_args()
    
    if not args.dry_run and not args.apply:
        print("Please specify either --dry-run or --apply")
        return

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found at {input_path}.")
        return
        
    print(f"[init] Parsing file: {input_path}")
    sec1_map, sec2_map = parse_markdown_changche(input_path)
    print(f"[init] Loaded {len(sec1_map)} 자율/동아리 records and {len(sec2_map)} 진로 records.")
    
    if not sec1_map and not sec2_map:
        print("[error] No records parsed. Please verify the markdown format.")
        return
        
    driver = connect_cdp(args.port)
    
    try:
        target_handle, target_frame = find_active_window_and_frame(driver)
        setup_target_context(driver, target_handle, target_frame)
    except Exception as e:
        print(f"Error finding active app: {e}")
        return

    # Fill comments
    fill_res = fill_comments(driver, sec1_map, sec2_map)
    if "error" in fill_res:
        print(f"  [Error] Error filling comments: {fill_res['error']}")
        return
        
    modified = fill_res.get("modified")
    count = fill_res.get("count", 0)
    details = fill_res.get("details", [])
    
    print(f"\nModifications: {count} cells updated. Details: {details}")
    
    grid_currently_modified = driver.execute_script(JS_FIND_APP + """
        var ds = inst.lookup("dsScrgRec");
        return ds ? ds.isModified() : false;
    """)
    
    # Save if needed
    if (modified or grid_currently_modified) and args.apply:
        print(f"  [Save] Saving (modified={modified} grid_currently_modified={grid_currently_modified})...")
        click_save(driver)
        
        print("  Waiting 7 seconds for transaction to complete...")
        time.sleep(7)
        
        if verify_saved(driver):
            print("  [OK] Saved successfully!")
        else:
            print("  [Warning] Save unverified - grid might still be modified")
            driver.execute_script(JS_FIND_APP + "var ds = inst.lookup('dsScrgRec'); if(ds) ds.revert();")
    elif (modified or grid_currently_modified) and args.dry_run:
        print("  [DRY-RUN] Changes made in browser grid, but not saved.")
    else:
        print("  [Info] No changes needed (already up-to-date or no revisions).")

if __name__ == "__main__":
    main()
