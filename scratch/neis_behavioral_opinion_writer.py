#!/usr/bin/env python3
"""
NEIS 행동특성 및 종합의견 자동 입력 스크립트.
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
    var inst = instances.find(ai => ai.app && ai.app.id.includes("els_sdlbg00_m00"));
    if (!inst) return {error: "App instance els_sdlbg00_m00 not found"};
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
                
    raise RuntimeError("Could not find any window or frame with the NEIS behavioral opinion CPR app active.")

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

def get_euc_kr_byte_len(s: str) -> int:
    return len(s.encode("euc-kr", errors="replace"))

def parse_markdown_opinions(filepath: Path) -> dict[str, str]:
    """Parse the markdown file and return a dictionary of student name -> opinion text."""
    content = filepath.read_text(encoding="utf-8")
    
    # Extract behavioral opinion section
    section_match = re.search(r"## 행동특성 및 종합의견.*?\n(.*?)\n## ", content, re.DOTALL)
    if section_match:
        section_text = section_match.group(1)
    else:
        # Fallback to look after ## 행동특성 및 종합의견 to end of file if no next section
        section_match_end = re.search(r"## 행동특성 및 종합의견.*?\n(.*)", content, re.DOTALL)
        section_text = section_match_end.group(1) if section_match_end else content

    # Find student records like:
    # **1. 강시우**
    # 차분하고 생각이 깊은 모습을 지니고 있으며...
    student_pattern = re.compile(r"\*\*(\d+)\.\s*([^\*]+)\*\*\s*\n([^\n]+)")
    matches = student_pattern.findall(section_text)
    
    records = {}
    for num, name, text in matches:
        name = name.strip()
        text = text.strip()
        records[name] = text
        print(f"[parsed] No.{num} {name}: {len(text)} chars, {get_euc_kr_byte_len(text)} bytes (EUC-KR)")
        
    return records

def parse_docx_opinions(filepath: Path) -> dict[str, str]:
    """Parse the docx file and return a dictionary of student name -> opinion text."""
    import docx
    doc = docx.Document(filepath)
    records = {}
    
    for p in doc.paragraphs:
        text = p.text.strip()
        if not text:
            continue
            
        lines = text.split('\n')
        if len(lines) >= 2:
            name_line = lines[0].strip()
            opinion_text = "\n".join(lines[1:]).strip()
            
            m = re.match(r"^(\d+)\.\s*([^\n]+)$", name_line)
            if m:
                student_name = m.group(2).strip()
                records[student_name] = opinion_text
                print(f"[parsed docx] {student_name}: {len(opinion_text)} chars, {get_euc_kr_byte_len(opinion_text)} bytes (EUC-KR)")
            
    return records

def fill_comments(driver, revisions_map: dict[str, str]) -> dict[str, any]:
    """Iterate dsScrgRec students and fill their behavioral opinions."""
    dismiss_alerts(driver)
    
    # Check what students are in the current grid
    grid_students = driver.execute_script(JS_FIND_APP + """
        var ds = inst.lookup("dsScrgRec");
        if (!ds) return {error: "dsScrgRec not found"};
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
        
        # Check if we have comment revisions for this student
        target_comment = revisions_map.get(student_name)
        
        if not target_comment:
            print(f"  [skip] No parsed opinion for student: '{student_name}'")
            continue
            
        # Get current comment in grid
        current_comment = driver.execute_script(JS_FIND_APP + f"""
            var ds = inst.lookup("dsScrgRec");
            return ds.getValue({row_idx}, "gnrlzOpiCn") || "";
        """)
        current_comment = decode_cpr_str(current_comment)
        
        if current_comment.strip() != target_comment.strip():
            # Update comment value programmatically in dataset
            js_target = json.dumps(target_comment, ensure_ascii=False)
            driver.execute_script(JS_FIND_APP + f"""
                var ds = inst.lookup("dsScrgRec");
                ds.setValue({row_idx}, "gnrlzOpiCn", {js_target});
            """)
            modified_count += 1
            updates_detail.append(f"{student_name}: updated opinion")
            
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

    # Load and parse comments
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found at {input_path}.")
        return
        
    print(f"[init] Parsing file: {input_path}")
    if input_path.suffix.lower() == ".docx":
        revisions_map = parse_docx_opinions(input_path)
    else:
        revisions_map = parse_markdown_opinions(input_path)
    print(f"[init] Loaded {len(revisions_map)} student opinion records.")
    
    if not revisions_map:
        print("[error] No student records parsed. Please verify the markdown format.")
        return
        
    driver = connect_cdp(args.port)
    
    # Locate active app context
    try:
        target_handle, target_frame = find_active_window_and_frame(driver)
        setup_target_context(driver, target_handle, target_frame)
    except Exception as e:
        print(f"Error finding active app: {e}")
        return

    # Fill comments
    fill_res = fill_comments(driver, revisions_map)
    if "error" in fill_res:
        print(f"  [Error] Error filling comments: {fill_res['error']}")
        return
        
    modified = fill_res.get("modified")
    count = fill_res.get("count", 0)
    details = fill_res.get("details", [])
    
    print(f"\nModifications: {count} students updated. Details: {details}")
    
    # Save if needed
    if modified and args.apply:
        print("  [Save] Saving...")
        click_save(driver)
        
        print("  Waiting 7 seconds for transaction to complete...")
        time.sleep(7)
        
        if verify_saved(driver):
            print("  [OK] Saved successfully!")
        else:
            print("  [Warning] Save unverified - grid might still be modified")
            # Revert
            driver.execute_script(JS_FIND_APP + "var ds = inst.lookup('dsScrgRec'); if(ds) ds.revert();")
    elif modified and args.dry_run:
        print("  [DRY-RUN] Changes made in browser grid, but not saved.")
    else:
        print("  [Info] No changes needed (already up-to-date or no revisions).")

if __name__ == "__main__":
    main()
