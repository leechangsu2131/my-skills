#!/usr/bin/env python3
"""
NEIS 행동특성 및 종합의견 누가기록 자동 입력 스크립트.

Usage:
  # 1) 나이스 화면 구조 진단
  python scratch/neis_cumulative_record_writer.py --diagnose

  # 2) Dry-run (그리드에 입력해보고 확인 후 자동 revert)
  python scratch/neis_cumulative_record_writer.py --dry-run

  # 3) 실반영 (학생별 순차 입력 후 자동 저장)
  python scratch/neis_cumulative_record_writer.py --apply
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
YEAR = "2026"
APP_ID = "els_sdlbg00_m01"  # 행동특성 누가기록 App ID

JS_FIND_APP = """
    var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var inst = instances.find(ai => ai.app && ai.app.id.includes("els_sdlbg00_m01"));
    if (!inst) return {error: "App instance els_sdlbg00_m01 not found"};
"""

def decode_cpr_str(s: str) -> str:
    """eXBuilder6 에서 반환되는 EUC-KR 인코딩 문자열 디코딩."""
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
    """브라우저 alert 닫기."""
    from selenium.common.exceptions import NoAlertPresentException
    try:
        alert = driver.switch_to.alert
        text = alert.text
        print(f"  [alert] Dismissed: '{text}'")
        alert.accept()
        time.sleep(1)
        dismiss_alerts(driver)
    except NoAlertPresentException:
        pass

def find_active_context(driver) -> tuple[str, str | None]:
    """Scan windows and frames to find where the 누가기록 screen is active."""
    handles = driver.window_handles
    for handle in handles:
        driver.switch_to.window(handle)
        driver.switch_to.default_content()
        try:
            has_cpr = driver.execute_script("return typeof cpr !== 'undefined';")
            if has_cpr:
                app_id = driver.execute_script("return cpr.core.Platform.INSTANCE.getAllRunningAppInstances().map(ai => ai.app.id).find(id => id.includes('els_sdlbg00_m01'));")
                if app_id:
                    print(f"[location] Found 누가기록 app in main frame of window '{driver.title}'")
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
                        app_id = driver.execute_script("return cpr.core.Platform.INSTANCE.getAllRunningAppInstances().map(ai => ai.app.id).find(id => id.includes('els_sdlbg00_m01'));")
                        if app_id:
                            print(f"[location] Found 누가기록 app in frame '{fid}' of window '{driver.title}'")
                            return handle, fid
                except Exception:
                    pass
        except Exception:
            pass
            
    raise RuntimeError("행동특성 누가기록 화면(els_sdlbg00_m01)을 찾을 수 없습니다. 나이스 화면이 열려 있고 조회 버튼을 누르셨는지 확인해 주세요.")

def setup_target_context(driver, target_handle, target_frame):
    """Switch context to target handle and frame."""
    driver.switch_to.window(target_handle)
    driver.switch_to.default_content()
    if target_frame:
        frames = driver.find_elements(By.TAG_NAME, "iframe")
        for frame in frames:
            if frame.get_attribute("id") == target_frame or frame.get_attribute("name") == target_frame:
                driver.switch_to.frame(frame)
                return
        raise RuntimeError(f"Frame {target_frame} not found")

def parse_cumulative_records(filepath: Path) -> dict[str, list[tuple[str, str]]]:
    """Parse the markdown file and return dict {student_name: [(date_str, opinion_text), ...]}."""
    content = filepath.read_text(encoding="utf-8")
    records: dict[str, list[tuple[str, str]]] = {}
    
    # Split by student blocks: **No. Name**
    blocks = re.split(r"\n\*\*(\d+)\.\s*", content)
    
    i = 1
    while i < len(blocks) - 1:
        num = blocks[i]
        body = blocks[i+1]
        i += 2
        
        name_match = re.match(r"([^*]+)\*\*", body)
        if not name_match:
            continue
        name = name_match.group(1).strip()
        
        # Parse observations: - (M/D) Text
        entries = re.findall(r"-\s*\((\d+)/(\d+)\)\s*(.+)", body)
        student_entries = []
        for m, d, text in entries:
            date_str = f"{YEAR}{int(m):02d}{int(d):02d}"
            student_entries.append((date_str, text.strip()))
            
        if student_entries:
            records[name] = student_entries
            
    return records

def click_save_student(driver):
    """Click student-specific save button and handle confirm modals in a loop for 6 seconds."""
    driver.execute_script(JS_FIND_APP + """
        var btn = inst.lookup("btnSaveStu");
        if (btn) btn.click();
    """)
    
    # Dismiss any popups that appear over 6 seconds
    for _ in range(6):
        time.sleep(1)
        dismiss_alerts(driver)
        driver.execute_script("""
            var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
            var modals = instances.filter(ai => ai && ai.app && (ai.app.id === "app/cmn/confirm" || ai.app.id === "app/cmn/alert"));
            modals.forEach(function(m) {
                try {
                    var container = m.getContainer();
                    if (!container) return;
                    var clicked = false;
                    function scan(ctrl) {
                        if (!ctrl || clicked) return;
                        var id = ctrl.id || "";
                        var val = ctrl.value || ctrl.text || "";
                        if (id === "btnOk" || id === "btnConfirm" || val === "확인" || val === "예" || val === "OK") {
                            if (typeof ctrl.click === 'function') {
                                try { ctrl.click(); clicked = true; } catch(e) {}
                            }
                        }
                        if (typeof ctrl.getChildren === 'function') {
                            var ch = ctrl.getChildren();
                            for (var j = 0; j < ch.length; j++) scan(ch[j]);
                        }
                    }
                    scan(container);
                } catch(e) {}
            });
        """)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="skills/classmanage-evaluate-to-neis/data/2026_1학기_행동특성_누가기록.md")
    parser.add_argument("--port", type=int, default=9222)
    parser.add_argument("--dry-run", action="store_true", help="Fill grid but do not save, then revert")
    parser.add_argument("--apply", action="store_true", help="Actually save to NEIS")
    parser.add_argument("--diagnose", action="store_true", help="Diagnose current screen only")
    parser.add_argument("--students", type=str, default="", help="Comma-separated student names to filter (e.g. 강시우)")
    parser.add_argument("--limit", type=int, default=0, help="Limit the number of students to process")
    args = parser.parse_args()
    
    if not args.dry_run and not args.apply and not args.diagnose:
        print("Please specify either --diagnose, --dry-run, or --apply")
        return

    driver = connect_cdp(args.port)
    
    try:
        target_handle, target_frame = find_active_context(driver)
        setup_target_context(driver, target_handle, target_frame)
    except Exception as e:
        print(f"Error finding active app: {e}")
        return

    if args.diagnose:
        # Diagnose datasets and controls
        res = driver.execute_script(JS_FIND_APP + """
            var dsResult = [];
            var dsNames = Object.keys(inst._dataModelMap || {});
            dsNames.forEach(function(name) {
                var dm = inst.lookup(name);
                if (!dm) return;
                var info = {id: name, type: dm.constructor.name || "unknown", rowCount: dm.getRowCount()};
                dsResult.push(info);
            });
            return dsResult;
        """)
        print(f"Active app: els_sdlbg00_m01. Datasets: {res}")
        return

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found at {input_path}.")
        return
        
    print(f"[init] Parsing file: {input_path}")
    records = parse_cumulative_records(input_path)
    print(f"[init] Loaded {len(records)} student observation records.")
    
    # Get student list from grid
    students = driver.execute_script(JS_FIND_APP + """
        var ds = inst.lookup("dsStu");
        if (!ds) return {error: "dsStu not found"};
        var list = [];
        for (var i = 0; i < ds.getRowCount(); i++) {
            list.push({
                index: i,
                name: ds.getValue(i, "stuFlnm") || ""
            });
        }
        return list;
    """)
    
    if isinstance(students, dict) and "error" in students:
        print(f"Error reading student list: {students['error']}")
        return
        
    print(f"Total students in grid: {len(students)}")
    
    # Filter students by name if specified
    filter_names = [n.strip() for n in args.students.split(",") if n.strip()]
    if filter_names:
        students = [s for s in students if decode_cpr_str(s["name"]).strip() in filter_names or re.sub(r"\(.*?\)", "", decode_cpr_str(s["name"])).strip() in filter_names]
        print(f"Filtered to {len(students)} students: {[decode_cpr_str(s['name']) for s in students]}")
        
    # Limit number of students if specified
    if args.limit > 0:
        students = students[:args.limit]
        print(f"Limited to {len(students)} students: {[decode_cpr_str(s['name']) for s in students]}")
        
    total_added = 0
    
    for stu in students:
        idx = stu["index"]
        raw_name = stu["name"]
        student_name = decode_cpr_str(raw_name)
        student_name_clean = re.sub(r"\(.*?\)", "", student_name).strip()
        
        target_records = records.get(student_name_clean)
        if not target_records:
            print(f"[{student_name_clean}] No records in parsed file, skipping.")
            continue
            
        # Select student row
        driver.execute_script(JS_FIND_APP + f"""
            var grid = inst.lookup("grdStu");
            grid.selectRows([{idx}]);
        """)
        time.sleep(1.5)
        dismiss_alerts(driver)
        
        # Read existing records for student
        existing = driver.execute_script(JS_FIND_APP + """
            var ds = inst.lookup("dsGicRecStu");
            if (!ds) return [];
            var list = [];
            for (var i = 0; i < ds.getRowCount(); i++) {
                list.push({
                    date: ds.getValue(i, "ghvrDevEnfcYmd") || "",
                    content: ds.getValue(i, "ghvrDevCn") || ""
                });
            }
            return list;
        """)
        
        # Decode existing records
        decoded_existing = []
        for r in existing:
            decoded_existing.append({
                "date": r["date"],
                "content": decode_cpr_str(r["content"]).strip()
            })
            
        student_added_count = 0
        
        for date_str, text in target_records:
            # Check if this record already exists
            found = False
            for r in decoded_existing:
                if r["date"] == date_str and r["content"] == text:
                    found = True
                    break
            
            if found:
                print(f"[{student_name_clean}] Record for {date_str} already exists. Skipping.")
                continue
                
            # Click btnAdd
            driver.execute_script(JS_FIND_APP + "inst.lookup('btnAdd').click();")
            time.sleep(0.5)
            
            # Find the new row index (inserted row that has empty content)
            new_row_idx = driver.execute_script(JS_FIND_APP + """
                var ds = inst.lookup("dsGicRecStu");
                // Check if last row is newly added and empty
                var lastIdx = ds.getRowCount() - 1;
                if (lastIdx >= 0 && ds.getValue(lastIdx, "ghvrDevCn") === "") {
                    return lastIdx;
                }
                // Check if first row is newly added and empty
                if (ds.getRowCount() > 0 && ds.getValue(0, "ghvrDevCn") === "") {
                    return 0;
                }
                // Fallback to search from end for empty inserted row
                for (var i = ds.getRowCount() - 1; i >= 0; i--) {
                    if (ds.getRowState(i) === 2 && ds.getValue(i, "ghvrDevCn") === "") {
                        return i;
                    }
                }
                return lastIdx;
            """)
            
            # Set values
            js_text = json.dumps(text, ensure_ascii=False)
            driver.execute_script(JS_FIND_APP + f"""
                var ds = inst.lookup("dsGicRecStu");
                ds.setValue({new_row_idx}, "ghvrDevEnfcYmd", "{date_str}");
                ds.setValue({new_row_idx}, "ghvrDevCn", {js_text});
            """)
            
            student_added_count += 1
            total_added += 1
            print(f"[{student_name_clean}] Added observation for {date_str}: {text[:20]}...")
            
        if student_added_count > 0:
            driver.execute_script(JS_FIND_APP + """
                var grid = inst.lookup("grdGicRecStu");
                if (grid) grid.redraw();
            """)
            
            if args.apply:
                print(f"[{student_name_clean}] Saving changes ({student_added_count} records added)...")
                click_save_student(driver)
                
                # Verify in a loop up to 5 seconds
                success = False
                for _ in range(5):
                    is_modified = driver.execute_script(JS_FIND_APP + """
                        var ds = inst.lookup("dsGicRecStu");
                        return ds ? ds.isModified() : false;
                    """)
                    if not is_modified:
                        success = True
                        break
                    time.sleep(1)
                
                if success:
                    print(f"[{student_name_clean}] Saved successfully!")
                else:
                    print(f"[{student_name_clean}] Save warning: detail dataset still modified!")
                    # Revert to be safe
                    driver.execute_script(JS_FIND_APP + "var ds = inst.lookup('dsGicRecStu'); if(ds) ds.revert();")
            elif args.dry_run:
                print(f"[{student_name_clean}] DRY-RUN: Added {student_added_count} records to grid. Reverting to keep state clean...")
                driver.execute_script(JS_FIND_APP + """
                    var ds = inst.lookup("dsGicRecStu");
                    if (ds) ds.revert();
                    var grid = inst.lookup("grdGicRecStu");
                    if (grid) grid.redraw();
                """)
                
    print(f"\n[Finished] Total records added/modified: {total_added}")

if __name__ == "__main__":
    main()
